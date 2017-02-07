
import os.path
from scriptcore.filesystem.archive import Archive


class Archiver(object):

    def archive(self, directory):
        """
        Archive a directory
        :param directory:   Directory
        :return:            Archive-name
        """

        if not os.path.exists(directory):
            raise RuntimeError('"%s" does not exist.' % directory)

        elif not os.path.isdir(directory):
            raise RuntimeError('"%s" is not a directory' % directory)

        directory_name = os.path.basename(directory)
        archive = '_%s.zip' % directory_name

        if not Archive.zip(directory, archive):
            raise RuntimeError('Failed to zip "%s"' % directory)

        return archive
