# [DEPRECATED] File Archiver

A file archiver that archives your files and generates descriptor-file.  
Ideal for saving space on your (cloud)storage!

**UPDATE:**
* Supporting archiving of Google Doc-files now!  
 *Google Doc-files on your local disk are only links. So adding them to
 an achive doesn't accomplish anything. Instead the tool makes actual
 backups of the content and adds them to the archive:*
  - .gdoc → .pdf & .docx
  - .gsheet → .pdf & .xslx
  - .gslides → .pdf & .pptx
  - .gdraw → .pdf


## Installation

1. Clone the project:

 ```bash
git clone git@github.com:LowieHuyghe/file-archiver.git
```
2. Move into the new directory:

 ```bash
cd file-archiver
```
3. Setup virtualenv and activate it
4. Install the requirements:

 ```bash
pip install -r requirements.txt
```
5. If you want to support archiving Google Doc-files:
  * Go to [Google API Dashboard](https://console.developers.google.com/apis/dashboard)
  * Enabled the *Google Drive API*
  * Go to *Credentials* and create *OAuth client ID Credentials*
  * Select *Other* and give the client a name
  * Once you close the dialog, click the download icon
  * Move the downloaded file to the root of this project
  * Rename it to *googleapi.credentials.json*


## Run

 ```bash
python archive.py -d mydirectory1 mydirectory2
```

> Note: Make sure your virtualenv is active when running the script.
