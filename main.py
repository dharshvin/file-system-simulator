import sqlite3
from pyscript import document

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

# Global state for current directory
current_dir_id = 1


# print to terminal function with pysript
def print_to_terminal(s=""):
    output_el = document.querySelector("#terminal-output")
    output_el.innerText += str(s) + "\n"
    
    # Auto-scroll the terminal window
    terminal = document.querySelector("#terminal")
    terminal.scrollTop = terminal.scrollHeight

def initialize_database():
     # Creates the database, table, and root directory
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(CREATE_ROOT_SQL)
        con.commit()
    # Changed to use print_to_terminal
    print_to_terminal(f"Database '{DB_NAME}' initialized.")

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
        # Changed to batch output for better web performance
        output = []
        for name, type in results:
            output.append(f"  {name}/" if type == 'directory' else f"  {name}")
        print_to_terminal("\n".join(output))

# mkdir - Create a new directory in the curr directory
def mkdir_command(current_dir_id, new_dir_name):
    if not new_dir_name or '/' in new_dir_name:
        print_to_terminal("Error: Invalid directory name.") 
        return
    
    # updated to prevent duplicate directory and avoid errors
    query = "INSERT INTO nodes (parent_id, name, type) VALUES (?, ?, 'directory')"
    try:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute(query, (current_dir_id, new_dir_name))
            con.commit()
    except sqlite3.IntegrityError:
        print_to_terminal(f"Error: An item named '{new_dir_name}' already exists here.") 

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
                print_to_terminal(f"Error: '{target_name}' is not a directory.") 
        else:
            print_to_terminal(f"Error: No such directory '{target_name}'.") 

        # stay in curr if nothing else            
        return current_dir_id

# touch - Create new file 
def touch_command(current_dir_id, new_file_name):
    # added basic validation for file name
    if not new_file_name or '/' in new_file_name:
        print_to_terminal("Error: Invalid file name.") 
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
        print_to_terminal("Usage: cat <file_name>") 
        return
    
    query = "SELECT type, content FROM nodes WHERE parent_id = ? AND name = ?"
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(query, (current_dir_id, file_name))
        result = cur.fetchone()
        if result:
            node_type, content = result
            if node_type == 'directory':
                print_to_terminal(f"Error: '{file_name}' is a directory.") 
            else:
                print_to_terminal(content if content is not None else "") 
        else:
            print_to_terminal(f"Error: No such file '{file_name}'.") 

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
            print_to_terminal(f"Error: No such file '{file_name}'.") 
            return
        file_id, file_type = result
        if file_type == 'directory':
            print_to_terminal(f"Error: Cannot write to '{file_name}', it is a directory.") 
            return
        
        # if it's a file then update content 
        try:
            cur.execute(update_query, (content, file_id))
            con.commit()
        except Exception as e:
            print_to_terminal(f"An unexpected error occurred: {e}") 

# rm - Remove file from curr directory
def rm_command(current_dir_id, node_name):
    # added prevention of removing '.' '..' or '/'
    if not node_name or node_name in ('..', '/'):
        print_to_terminal("Error: Invalid name for removal.") 
        return
    
    # Uses delete cascade from table to handle recursively deleting chlidren too
    query = "DELETE FROM nodes WHERE parent_id = ? AND name = ?"
    
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        try:
            # Foreign key constraints (and CASCADE) must be enabled per-connection in SQLite (from new script)
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(query, (current_dir_id, node_name))
            con.commit()
            if cur.rowcount == 0:
                print_to_terminal(f"Error: No such file or directory '{node_name}'.") 
        except Exception as e:
            print_to_terminal(f"An unexpected error occurred: {e}") 

# Helper function to get the string path with directory ID.
def get_path_string_for_id(dir_id):
    if dir_id == 1:
        return "/"

    path_parts = []
    temp_id = dir_id
    
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        while temp_id is not None and temp_id != 1:
            query = "SELECT name, parent_id FROM nodes WHERE id = ?"
            cur.execute(query, (temp_id,))
            result = cur.fetchone()
            if result:
                name, parent_id = result
                path_parts.insert(0, name)
                temp_id = parent_id
            else:
                break
    
    final_path = "/" + "/".join(path_parts)
    return final_path

# pwd - Print the current working directory path
def pwd_command(current_dir_id):
    # uses the helper function
    path_string = get_path_string_for_id(current_dir_id)
    print_to_terminal(path_string)

# replaced the original main_loop()

def get_prompt():
    # Gets the full path string instead of just the ID
    path_string = get_path_string_for_id(current_dir_id)
    return f"fs:{path_string}$ "

# handles enter key press
def handle_keypress(event):
    if event.key != "Enter":
        return
        
    global current_dir_id
    
    input_el = document.querySelector("#command-input")
    command_input = input_el.value.strip()

    print_to_terminal(get_prompt() + command_input)

    input_el.value = ""

    # Process the command 
    if not command_input:
        prompt_el = document.querySelector("#prompt")
        prompt_el.innerText = get_prompt()
        return

    # parse input, split string into a list of words and convert to command to lowercase
    parts = command_input.split()
    command = parts[0].lower()
    
    # if block to validate and execute command
    if command == "exit":
        print_to_terminal("Exiting. (Reload the page to restart.)")
        input_el.disabled = True
    
    elif command == "ls":
        ls_command(current_dir_id)
        
    elif command == "mkdir":
        if len(parts) > 1:
            mkdir_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: mkdir <directory_name>")
    
    elif command == "cd":
        if len(parts) > 1:
            current_dir_id = cd_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: cd <directory_name | .. | />")
    
    elif command == "touch":
        if len(parts) > 1:
            touch_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: touch <file_name>")

    elif command == "cat":
        if len(parts) > 1:
            cat_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: cat <file_name>")
    
    elif command == "write":
        # updated to require at least 3 parts 
        if len(parts) < 3:
            print_to_terminal("Usage: write <filename> <content...>")
        else:
            _parts = command_input.split(maxsplit=2)
            file_name = _parts[1]
            content = _parts[2]
            write_command(current_dir_id, file_name, content)
    
    elif command == "rm":
        if len(parts) > 1:
            rm_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: rm <file_or_directory_name>")

    elif command == "pwd": 
        pwd_command(current_dir_id)

    else:
        print_to_terminal(f"Command not found: '{command}'")
    
    # Update the prompt for the next line
    if not input_el.disabled:
        prompt_el = document.querySelector("#prompt")
        prompt_el.innerText = get_prompt()

def main_setup():
    initialize_database()
    print_to_terminal("Welcome to the File System Simulator!")
    print_to_terminal("Commands: 'ls', 'mkdir', 'cd', 'touch', 'cat', 'write', 'rm', 'pwd', 'exit'.") 

    prompt_el = document.querySelector("#prompt")
    prompt_el.innerText = get_prompt()
    
    document.querySelector("#command-input").focus()

# main setup run
main_setup()