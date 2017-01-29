
from scriptcore.console.cuiscript import CuiScript
from filearchiver.archiver.archiver import Archiver
from filearchiver.archiver.descriptor import Descriptor
import os.path
from scriptcore.filesystem.path import Path


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

        self._register_option('d', 'Directories to process', type='list')

        self._archiver = Archiver()
        self._descriptor = Descriptor()

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
            try:
                archive = self._archiver.archive(directory)
                if not archive:
                    self.output('Something went wrong while archiving "%s"' % directory, 'error')
                    continue

                description = self._descriptor.describe(directory, archive)
                if not description:
                    self.output('Something went wrong while describing "%s"' % directory, 'error')
                    continue

                archive_size = Path.readable_size(os.path.getsize(archive))
                directory_size = Path.readable_size(Path.get_dir_size(directory))
                self.output('Description and Archive created for "%s" (%s -> %s)' % (directory, directory_size, archive_size), 'success')

            except RuntimeError as e:
                self.output('Error: %s' % e, 'error')
