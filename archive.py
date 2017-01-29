
if __name__ == '__main__':
    import os.path
    import filearchiver.archive
    from filearchiver.archive import Archive

    base_path = os.path.dirname(os.path.realpath(__file__))
    archive = Archive(base_path)
    archive.run()
