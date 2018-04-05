
from scriptcore.cuiscript import CuiScript
from filearchiver.archiver.archiver import Archiver
from filearchiver.archiver.descriptor import Descriptor
import os
from scriptcore.filesystem.path import Path
from scriptcore.console.option import Option
import json
from oauth2client.client import flow_from_clientsecrets
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.discovery import build
import httplib2
from scriptcore.encoding.encoding import Encoding


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
        self._google_drive_supported_extensions = {
            '.gdoc': 'application/vnd.google-apps.document',
            '.gsheet': 'application/vnd.google-apps.spreadsheet',
            '.gslides': 'application/vnd.google-apps.presentation',
            '.gdraw': 'application/vnd.google-apps.drawing',
            '.gscript': 'application/vnd.google-apps.script'
        }
        self._google_drive_supported_mime_types = {
            'application/vnd.google-apps.document': [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.oasis.opendocument.text',
                # 'application/rtf',  # Gives internal error on Google Drive API
                'application/zip',
                'text/plain'
            ],
            'application/vnd.google-apps.spreadsheet': [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/x-vnd.oasis.opendocument.spreadsheet',
                'application/zip',
                'text/csv'
            ],
            'application/vnd.google-apps.presentation': [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.oasis.opendocument.presentation',
                'text/plain'
            ],
            'application/vnd.google-apps.drawing': [
                'application/pdf',
                'image/jpeg',
                'image/png',
                'image/svg+xml'
            ],
            'application/vnd.google-apps.script': [
                'application/vnd.google-apps.script+json'
            ]
        }
        self._google_drive_associated_extensions = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            'application/vnd.oasis.opendocument.text': '.odt',
            'application/x-vnd.oasis.opendocument.spreadsheet': '.ods',
            'application/vnd.oasis.opendocument.presentation': '.odp',
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/svg+xml': '.svg',
            'application/rtf': '.rtf',
            'text/plain': '.txt',
            'text/csv': '.csv',
            'application/zip': '.zip',
            'application/vnd.google-apps.script+json': '.json'
        }
        self._google_drive_unsupported_extensions = ['.gform', '.gmap', '.gsite']

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

        for dir_path, dirs, files in os.walk(directory):
            for file_name in files:
                file_path = os.path.join(dir_path, file_name)
                file_name_without_extension, extension = os.path.splitext(file_name)

                # Unsupported extension
                if extension in self._google_drive_unsupported_extensions:
                    description = 'Can\'t backup "%s" from Google Drive as exporting is not supported.\n' \
                                  '  Would you like to continue with "%s"?' % (file_path, directory)
                    if not self.input.yes_no(description):
                        return False

                # Supported extension
                elif extension in self._google_drive_supported_extensions:
                    # Get Doc id
                    with open(file_path, 'rb') as open_file:
                        google_drive_file_content = json.load(open_file)

                        if 'doc_id' not in google_drive_file_content:
                            description = 'Can\'t backup "%s" from Google Drive as file-id could not be found.\n' \
                                          '  Would you like to continue with "%s"?' % (file_path, directory)
                            if not self.input.yes_no(description):
                                return False

                        google_drive_file_id = Encoding.normalize(google_drive_file_content['doc_id'])

                    # Drive service
                    drive_service = self._get_google_drive_service()
                    if drive_service is None:
                        description = 'Could not initiate Google Drive service to backup Google Docs.\n' \
                                      '  For more info: see README.md.\n' \
                                      '  Would you like to continue with "%s"?' % directory
                        if not self.input.yes_no(description):
                            return False

                    # Backup for each associated extension
                    mime_type = self._google_drive_supported_extensions[extension]
                    for associated_mime_type in self._google_drive_supported_mime_types[mime_type]:
                        associated_extension = self._google_drive_associated_extensions[associated_mime_type]

                        # Fetch response
                        response = drive_service.files().export(fileId=google_drive_file_id, mimeType=associated_mime_type).execute()
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
