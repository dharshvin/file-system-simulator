# SQLite File System Simulator

A simple, command-line file system simulator written in Python. It uses an SQLite database to create a persistent file system.
All files, directories, and their contents are stored in a database table.

##  Commands


  * `ls`
    Lists all files and directories in the current directory. Directories are marked with a `/`.

  * `mkdir <directory_name>`
    Creates a new directory with the specified name in the current directory.

  * `cd <directory_name>`
    Changes the current directory.

      * `cd /` - Go to the root directory.
      * `cd ..` - Go to the parent directory.
      * `cd subdir` - Go to a child directory named `subdir`.

  * `touch <file_name>`
    Creates a new, empty file. If the file already exists, this command does nothing.

  * `cat <file_name>`
    Prints the contents of a file to the console.

  * `write <file_name> <content...>`
    Writes (or overwrites) text content to a file. The content can include spaces.

      * Example: `write notes.txt This is my new note.`

  * `rm <name>`
    Removes a file or directory from the current directory.

      * If you remove a directory, all its contents and children will be recursively deleted.

  * `exit`
    Quits the file system simulator.