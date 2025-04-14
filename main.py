import sqlite3

# Code to initialize database (only initializes if there is no existing database)

DB_NAME = 'filesystem.db'

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('file', 'directory')),
    content TEXT,
    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE,
    UNIQUE(parent_id, name)
);
"""

# added IGNORE to prevent errors
CREATE_ROOT_SQL = """
INSERT OR IGNORE INTO nodes (id, parent_id, name, type) 
VALUES (1, NULL, '/', 'directory');
"""

def initialize_database():
     # Creates the database, table, and root directory
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(CREATE_ROOT_SQL)
        con.commit()
    print(f"Database '{DB_NAME}' initialized.")

# Commands: ls, mkdir, cd, touch, cat, write, rm 

# ls - List the contents in the current directory
def ls_command(current_dir_id):
    # Find all children
    query = "SELECT name, type FROM nodes WHERE parent_id = ?"
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(query, (current_dir_id,))
        results = cur.fetchall()
        if not results: return
        
        # Loop through results and print direcotries with a /
        for name, type in results:
            print(f"  {name}/" if type == 'directory' else f"  {name}")

# mkdir - Create a new directory in the curr directory
def mkdir_command(current_dir_id, new_dir_name):
    if not new_dir_name or '/' in new_dir_name:
        print("Error: Invalid directory name.")
        return
    
    # updated to prevent duplicate directory and avoid errors
    query = "INSERT INTO nodes (parent_id, name, type) VALUES (?, ?, 'directory')"
    try:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute(query, (current_dir_id, new_dir_name))
            con.commit()
    except sqlite3.IntegrityError:
        print(f"Error: An item named '{new_dir_name}' already exists here.")

# cd - Change the current directory and return new dir ID or old if fails
def cd_command(current_dir_id, target_name):
    # added 'cd /' to go back to root
    if target_name == '/': return 1

    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()

        # added 'cd ..' for parent dir
        if target_name == '..':
            if current_dir_id == 1: return 1
            query = "SELECT parent_id FROM nodes WHERE id = ?"
            cur.execute(query, (current_dir_id,))
            result = cur.fetchone()
            return result[0] if result and result[0] is not None else 1
        
        # SQL query to find node in curr directory with target_name
        query = "SELECT id, type FROM nodes WHERE parent_id = ? AND name = ?"
        cur.execute(query, (current_dir_id, target_name))
        result = cur.fetchone()

        if result:
            target_id, target_type = result
            if target_type == 'directory':
                return target_id
            else:
                print(f"Error: '{target_name}' is not a directory.")
        else:
            print(f"Error: No such directory '{target_name}'.")

        # stay in curr if nothing else            
        return current_dir_id

# touch - Create new file 
def touch_command(current_dir_id, new_file_name):
    # added basic validation for file name
    if not new_file_name or '/' in new_file_name:
        print("Error: Invalid file name.")
        return
    
    #added try to prevent duplicate files
    query = "INSERT INTO nodes (parent_id, name, type) VALUES (?, ?, 'file')"
    try:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute(query, (current_dir_id, new_file_name))
            con.commit()
    except sqlite3.IntegrityError:
        pass 

#cat - Print from a file
def cat_command(current_dir_id, file_name):
    if not file_name:
        print("Usage: cat <file_name>")
        return
    
    query = "SELECT type, content FROM nodes WHERE parent_id = ? AND name = ?"
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(query, (current_dir_id, file_name))
        result = cur.fetchone()
        if result:
            node_type, content = result
            if node_type == 'directory':
                print(f"Error: '{file_name}' is a directory.")
            else:
                print(content if content is not None else "")
        else:
            print(f"Error: No such file '{file_name}'.")

# write: writes content to a specific file
def write_command(current_dir_id, file_name, content):
    # SQL queries to find the file and its type + update the content
    find_query = "SELECT id, type FROM nodes WHERE parent_id = ? AND name = ?"
    update_query = "UPDATE nodes SET content = ? WHERE id = ?"

    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(find_query, (current_dir_id, file_name))
        result = cur.fetchone()
        if not result:
            print(f"Error: No such file '{file_name}'.")
            return
        file_id, file_type = result
        if file_type == 'directory':
            print(f"Error: Cannot write to '{file_name}', it is a directory.")
            return
        
        # if it's a file then update content 
        try:
            cur.execute(update_query, (content, file_id))
            con.commit()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

# rm - Remove file from curr directory
def rm_command(current_dir_id, node_name):
    # added prevention of removing '.' '..' or '/'
    if not node_name or node_name in ('..', '/'):
        print("Error: Invalid name for removal.")
        return
    
    # Uses delete cascade from table to handle recursively deleting chlidren too
    query = "DELETE FROM nodes WHERE parent_id = ? AND name = ?"
    
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        try:
            cur.execute(query, (current_dir_id, node_name))
            con.commit()
            if cur.rowcount == 0:
                print(f"Error: No such file or directory '{node_name}'.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

# Main loop for shell
def main_loop():
    """The main interactive shell for the file system."""
    current_dir_id = 1
    
    print("Welcome to the File System Simulator!")
    print("Commands: 'ls', 'mkdir', 'cd', 'touch', 'cat', 'write', 'rm', 'pwd', 'exit'.")
    
    while True:
        prompt = f"fs (id:{current_dir_id})$ " 
        
        # read user input and ask again if no input
        command_input = input(prompt).strip()
        if not command_input:
            continue
        
        # parse input, split string into a list of words
        # and convert to command to lowercase
        parts = command_input.split()
        command = parts[0].lower()
        
        # if block to validate and execute command
        if command == "exit":
            print("Exiting.")
            break
            
        elif command == "ls":
            ls_command(current_dir_id)
            
        elif command == "mkdir":
            if len(parts) > 1:
                mkdir_command(current_dir_id, parts[1])
            else:
                print("Usage: mkdir <directory_name>")
        
        elif command == "cd":
            if len(parts) > 1:
                current_dir_id = cd_command(current_dir_id, parts[1])
            else:
                print("Usage: cd <directory_name | .. | />")
        
        elif command == "touch":
            if len(parts) > 1:
                touch_command(current_dir_id, parts[1])
            else:
                print("Usage: touch <file_name>")

        elif command == "cat":
            if len(parts) > 1:
                cat_command(current_dir_id, parts[1])
            else:
                print("Usage: cat <file_name>")
        
        elif command == "write":
            # updated to require at least 3 parts 
            if len(parts) < 3:
                print("Usage: write <filename> <content...>")
            else:
                _parts = command_input.split(maxsplit=2)
                file_name = _parts[1]
                content = _parts[2]
                write_command(current_dir_id, file_name, content)
        
        elif command == "rm":
            if len(parts) > 1:
                rm_command(current_dir_id, parts[1])
            else:
                print("Usage: rm <file_or_directory_name>")
            
        else:
            print(f"Command not found: '{command}'")

# Main 

if __name__ == "__main__":
    initialize_database()
    main_loop()