
import os
from scriptcore.filesystem.path import Path


class Descriptor(object):

    def describe(self, directory, archive):
        """
        Describe the archive
        :param directory:   The directory
        :param archive:     The archive with compressed directory
        :return:            void
        """

        archive_size = os.path.getsize(archive)
        directory_size = Path.get_dir_size(directory)

        output = ''

        output += '# %s' % os.path.basename(directory)
        output += '\n'
        output += '\nThis file describes the contents of `%s`.' % os.path.basename(archive)
        output += '\n'
        output += '\n## Contents'

        for dirpath, direnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                output += '\n*%s* _(%s)_' % (file_path, Path.readable_size(os.path.getsize(file_path)))

        output += '\n'
        output += '\n## Info'

        output += '\n- Original size: %s' % Path.readable_size(directory_size)
        archive_percentage = round(float(archive_size) / directory_size * 100)
        output += '\n- Archived size: %s _(%i%%)_' % (Path.readable_size(archive_size), archive_percentage)
        save_percentage = - round(float(directory_size - archive_size) / directory_size * 100)
        output += '\n- Save space: %s _(%i%%)_' % (Path.readable_size(directory_size - archive_size), save_percentage)
        output += '\n'

        description_name = '_%s.md' % os.path.basename(directory)
        description = open(description_name, 'w+')
        try:
            description.write(output)
        finally:
            description.close()

        return description_name
