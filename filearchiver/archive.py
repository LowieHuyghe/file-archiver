
from scriptcore.cuiscript import CuiScript
from filearchiver.archiver.archiver import Archiver
from filearchiver.archiver.descriptor import Descriptor
import os
from scriptcore.filesystem.path import Path
from scriptcore.console.option import Option

from oauth2client.client import flow_from_clientsecrets
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.discovery import build
import httplib2
from scriptcore.filesystem.mimetype import MimeType


class Archive(CuiScript):

    def __init__(self, base_path, arguments=None):
        """
        Construct the script
        :param base_path:   The base path
        :param arguments:   The arguments
        """

        title = 'Archive'
        description = 'Archive files'

        super(Archive, self).__init__(base_path, title, description, arguments=arguments)

        self._register_option('d', 'Directories to process', type=Option.type_list)

        self._archiver = Archiver()
        self._descriptor = Descriptor()

        self._google_drive_service = None
        self._google_drive_supported_extensions = ['.gdoc', '.gsheet', '.gslides', '.gdraw']
        self._google_drive_unsupported_extensions = ['.gform', '.gmap', '.gsite']
        self._google_drive_associated_extensions = {
            '.gdoc': ['.pdf', '.docx'],
            '.gsheet': ['.pdf', '.xslx'],
            '.gslides': ['.pdf', '.pptx'],
            '.gdraw': ['.pdf']
        }

    def _run(self):
        """
        Actually run the script
        :return:    void
        """

        if not self._has_option('d'):
            self.help()
            return
        elif not self._get_option('d'):
            self.output('No directories given', 'error')
            return

        for directory in self._get_option('d'):
            self.output('Processing "%s"' % directory, 'title')
            try:
                self.output('Validating and backing up Google Docs', 'info')
                if not self._validate_directory(directory):
                    self.output('Could not validate "%s"' % directory, 'error')
                    continue

                self.output('Archiving', 'info')
                archive = self._archiver.archive(directory)
                if not archive:
                    self.output('Something went wrong while archiving "%s"' % directory, 'error')
                    continue

                self.output('Describing', 'info')
                description = self._descriptor.describe(directory, archive)
                if not description:
                    self.output('Something went wrong while describing "%s"' % directory, 'error')
                    continue

                archive_size = Path.readable_size(os.path.getsize(archive))
                directory_size = Path.readable_size(Path.get_dir_size(directory))
                self.output('Description and Archive created for "%s" (%s -> %s)' % (directory, directory_size, archive_size), 'success')

            except RuntimeError as e:
                self.output('Error: %s' % e, 'error')

    def _validate_directory(self, directory):
        """
        Validate the given directory
        :return:    void
        """

        unsupported_extension_continue = False

        for dir_path, dir_names, files in os.walk(directory):
            dir_name = os.path.basename(dir_path)
            for file in files:
                file_name, extension = os.path.splitext(file)

                # Unsupported extension
                if extension in self._google_drive_unsupported_extensions:
                    if not unsupported_extension_continue:
                        description = 'Can\'t backup "%s" from Google Drive as exporting is not supported.\n' \
                                      '  Would you like to continue with "%s"?' % (os.path.join(dir_path, file), directory)
                        if self.input.yes_no(description):
                            unsupported_extension_continue = True
                        else:
                            return False

                # Supported extension
                if extension in self._google_drive_supported_extensions:
                    # Drive service
                    drive_service = self._get_google_drive_service()
                    if drive_service is None:
                        description = 'Could not initiate Google Drive service to backup Google Docs.\n' \
                                      '  For more info: see README.md.\n' \
                                      '  Would you like to continue with "%s"?' % directory
                        return self.input.yes_no(description)

                    # Setup query
                    mime_type, encoding = MimeType.guess_type(extension)
                    query = 'name = "%s" and mimeType = "%s"' % (file_name, mime_type)

                    # Fetch result
                    response = drive_service.files().list(q=query).execute()
                    response_files = response.get('files', [])

                    # No results
                    if not len(response_files):
                        description = 'Couldn\'t backup "%s" from Google Drive.\n' \
                                      '  Would you like to continue with "%d"?' % (os.path.join(dir_path, file), directory)
                        if not self.input.yes_no(description):
                            return False
                        continue

                    # More than one match found, filter
                    response_files_info = dict()
                    if len(response_files) > 1:
                        def filter_response_files(response_file):
                            response = drive_service.files().get(fileId=response_file.get('id'), fields='parents, createdTime, modifiedTime').execute()
                            response_files_info[response_file.get('id')] = response
                            if not len(response.get('parents')):
                                return True
                            response = drive_service.files().get(fileId=response.get('parents')[0], fields='name').execute()
                            return dir_name == response.get('name')

                        response_files = filter(filter_response_files, response_files)

                    # Still more than one match
                    if len(response_files) > 1:
                        description = 'There are multiple files found that match "%s".\n' \
                                      '  Which one is the correct one?' % os.path.join(dir_path, file)
                        pick_options = []
                        for response_file in response_files:
                            response_file_info = response_files_info[response_file.get('id')]
                            created_time = '%s %s' % (response_file_info.get('createdTime')[0:10], response_file_info.get('createdTime')[11:19])
                            modified_time = '%s %s' % (response_file_info.get('modifiedTime')[0:10], response_file_info.get('modifiedTime')[11:19])
                            pick_options.append('%s (created:%s, modified:%s)' % (response_file.get('name'), created_time, modified_time))
                        picked_index = None
                        while picked_index is None:
                            picked_index = self.input.pick(pick_options, description)

                    response_file = response_files[0]

                    # Backup for each associated extension
                    for associated_extension in self._google_drive_associated_extensions[extension]:
                        associated_mime_type, associated_encoding = MimeType.guess_type(associated_extension)

                        # Fetch response
                        response = drive_service.files().export(fileId=response_file.get('id'), mimeType=associated_mime_type).execute()
                        # Save to disk
                        backup_file_name = os.path.join(dir_path, '%s.bak%s' % (file_name, associated_extension))
                        with open(backup_file_name, 'w') as backup_file:
                            backup_file.write(response)

        return True

    def _get_google_drive_service(self):
        """
        Get drive service
        :return:    Drive service
        """

        if self._google_drive_service is not None:
            return self._google_drive_service

        credentials_file = self.get_path('googleapi.credentials.json')
        if not os.path.exists(credentials_file):
            return None

        credentials = None

        # Try storage
        storage_file = self.get_path('googleapi.credentials.storage')
        storage = Storage(storage_file)
        if os.path.exists(storage_file):
            credentials = storage.get()

        # Try logging in
        if credentials is None or credentials.invalid:
            flow = flow_from_clientsecrets(credentials_file, scope='https://www.googleapis.com/auth/drive.readonly')
            flags = tools.argparser.parse_args(args=[])
            credentials = tools.run_flow(flow, storage, flags)

        # Make authorized drive service
        http = httplib2.Http()
        http = credentials.authorize(http)
        self._google_drive_service = build('drive', 'v3', http=http)

        return self._google_drive_service
