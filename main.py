import sqlite3
from pyscript import document

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

COMMAND_HELP = {
    "help": "Usage: help [command]\n\nShow this help message or detailed help for a specific command.",
    "ls": "Usage: ls [path]\n\nList the contents of the specified directory (or the current directory if no path is given).",
    "mkdir": "Usage: mkdir <path>\n\nCreate a new directory at the specified path.",
    "cd": "Usage: cd <path>\n\nChange the current directory to the specified path. Use '..' to go up one level or '/' for root.",
    "touch": "Usage: touch <path>\n\nCreate a new empty file at the specified path. Does nothing if the file already exists.",
    "cat": "Usage: cat <path>\n\nPrint the contents of the file at the specified path to the terminal.",
    "write": "Usage: write <path> <content...>\n\nWrite the provided content to the file at the specified path, overwriting any existing content.",
    "rm": "Usage: rm <path>\n\nRemove the file or directory at the specified path. This is recursive and permanent.",
    "pwd": "Usage: pwd\n\nPrint the full path of the current working directory.",
    "exit": "Usage: exit\n\nStop the terminal session. (Page must be reloaded to restart)."
}

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
    print_to_terminal(f"'{DB_NAME}' initialized.")

def resolve_path_to_node(current_dir_id, path_str):
    """
    Resolves a path string to a node.
    Returns (id, type, parent_id, name) or (None, 'nonexistent', parent_id, name)
    """
    if not path_str:
        return (current_dir_id, 'directory', None, None) 

    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()

        if path_str.startswith('/'):
            current_node_id = 1 # Start from root
            path_parts = path_str.strip('/').split('/')
        else:
            current_node_id = current_dir_id # Start from current dir
            path_parts = path_str.split('/')
        
        if path_str == '/':
             return (1, 'directory', None, '/')

        target_node_id = current_node_id
        target_node_type = 'directory'
        target_parent_id = None
        target_name = ''

        cur.execute("SELECT parent_id FROM nodes WHERE id = ?", (target_node_id,))
        parent_result = cur.fetchone()
        target_parent_id = parent_result[0] if parent_result else None

        for part in path_parts:
            if not part or part == '.':
                cur.execute("SELECT parent_id FROM nodes WHERE id = ?", (target_node_id,))
                parent_result = cur.fetchone()
                target_parent_id = parent_result[0] if parent_result else None
                continue

            if part == '..':
                if target_node_id == 1: continue
                target_node_id = target_parent_id if target_parent_id is not None else 1
                
                cur.execute("SELECT type, name, parent_id FROM nodes WHERE id = ?", (target_node_id,))
                result = cur.fetchone()
                target_node_type = result[0] if result else 'directory'
                target_name = result[1] if result else '..'
                target_parent_id = result[2] if result and result[2] is not None else 1
                
                continue
            
            query = "SELECT id, type, parent_id, name FROM nodes WHERE parent_id = ? AND name = ?"
            cur.execute(query, (target_node_id, part))
            result = cur.fetchone()

            if result:
                target_node_id, target_node_type, target_parent_id, target_name = result
                if target_node_type == 'file' and part != path_parts[-1]:
                    print_to_terminal(f"Error: '{part}' in path is a file.")
                    return (None, None, None, None)
            else:
                if part == path_parts[-1]:
                    return (None, 'nonexistent', target_node_id, part) 
                    
                print_to_terminal(f"Error: No such file or directory '{part}'.")
                return (None, None, None, None)
        
        return (target_node_id, target_node_type, target_parent_id, target_name)
    
# Commands: ls, mkdir, cd, touch, cat, write, rm, pwd, help

# ls - List the contents in the current directory
def ls_command(current_dir_id, path_str=None):
    target_dir_id = current_dir_id
    if path_str:
        node_id, node_type, _, _ = resolve_path_to_node(current_dir_id, path_str)
        if node_id is None:
            print_to_terminal(f"Error: Cannot access '{path_str}': No such file or directory")
            return
        if node_type != 'directory':
            print_to_terminal(f"Error: '{path_str}' is not a directory.")
            return
        target_dir_id = node_id
    
    query = "SELECT name, type FROM nodes WHERE parent_id = ?"
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(query, (target_dir_id,))
        results = cur.fetchall()
        if not results: return
        
        output = [f"  {name}/" if type == 'directory' else f"  {name}" for name, type in results]
        print_to_terminal("\n".join(output))

# mkdir - Create a new directory in the curr directory
def mkdir_command(current_dir_id, new_path_str):
    node_id, node_type, parent_id, new_name = resolve_path_to_node(current_dir_id, new_path_str)
    
    if node_id is not None:
        print_to_terminal(f"Error: '{new_path_str}' already exists.")
        return
    
    if node_type == 'nonexistent' and parent_id is not None:
        if '/' in new_name:
             print_to_terminal(f"Error: Invalid directory name '{new_name}'.")
             return
             
        query = "INSERT INTO nodes (parent_id, name, type) VALUES (?, ?, 'directory')"
        try:
            with sqlite3.connect(DB_NAME) as con:
                cur = con.cursor()
                cur.execute(query, (parent_id, new_name))
                con.commit()
        except sqlite3.IntegrityError:
            print_to_terminal(f"Error: An item named '{new_name}' already exists here.")
    else:
        print_to_terminal(f"Error: Cannot create directory '{new_path_str}'.")

# cd - Change the current directory and return new dir ID or old if fails
def cd_command(current_dir_id, target_path_str):
    node_id, node_type, _, _ = resolve_path_to_node(current_dir_id, target_path_str)
    
    if node_id:
        if node_type == 'directory':
            return node_id
        else:
            print_to_terminal(f"Error: '{target_path_str}' is not a directory.")
    else:
        print_to_terminal(f"Error: No such directory '{target_path_str}'.")

    return current_dir_id # Stay in current dir on failure

# touch - Create new file 
def touch_command(current_dir_id, new_path_str):
    if not new_path_str:
        print_to_terminal("Usage: touch <file_path>")
        return

    node_id, node_type, parent_id, new_name = resolve_path_to_node(current_dir_id, new_path_str)

    if node_id is not None:
        pass
        return

    if node_type == 'nonexistent' and parent_id is not None:
        if '/' in new_name:
             print_to_terminal(f"Error: Invalid file name '{new_name}'.")
             return

        query = "INSERT INTO nodes (parent_id, name, type) VALUES (?, ?, 'file')"
        try:
            with sqlite3.connect(DB_NAME) as con:
                cur = con.cursor()
                cur.execute(query, (parent_id, new_name))
                con.commit()
        except sqlite3.IntegrityError:
            pass 
    else:
        print_to_terminal(f"Error: Cannot touch '{new_path_str}'.")

#cat - Print from a file
def cat_command(current_dir_id, file_path_str):
    if not file_path_str:
        print_to_terminal("Usage: cat <file_path>") 
        return
    
    node_id, node_type, _, _ = resolve_path_to_node(current_dir_id, file_path_str)

    if node_id:
        if node_type == 'directory':
            print_to_terminal(f"Error: '{file_path_str}' is a directory.")
        else:
            query = "SELECT content FROM nodes WHERE id = ?"
            with sqlite3.connect(DB_NAME) as con:
                cur = con.cursor()
                cur.execute(query, (node_id,))
                result = cur.fetchone()
                print_to_terminal(result[0] if result and result[0] is not None else "")
    else:
        print_to_terminal(f"Error: No such file '{file_path_str}'.")

# write: writes content to a specific file
def write_command(current_dir_id, file_path_str, content):
    node_id, node_type, _, _ = resolve_path_to_node(current_dir_id, file_path_str)

    if not node_id:
        print_to_terminal(f"Error: No such file '{file_path_str}'.") 
        return
    if node_type == 'directory':
        print_to_terminal(f"Error: Cannot write to '{file_path_str}', it is a directory.") 
        return
        
    update_query = "UPDATE nodes SET content = ? WHERE id = ?"
    try:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute(update_query, (content, node_id))
            con.commit()
    except Exception as e:
        print_to_terminal(f"An unexpected error occurred: {e}")

# rm - Remove file from curr directory
def rm_command(current_dir_id, node_path_str):
    if not node_path_str:
        print_to_terminal("Usage: rm <path>")
        return

    node_id, _, _, _ = resolve_path_to_node(current_dir_id, node_path_str)

    if not node_id:
        print_to_terminal(f"Error: No such file or directory '{node_path_str}'.")
        return

    if node_id == 1:
        print_to_terminal("Error: Cannot remove root directory.")
        return
    
    query = "DELETE FROM nodes WHERE id = ?"
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        try:
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(query, (node_id,))
            con.commit()
            if cur.rowcount == 0:
                print_to_terminal(f"Error: No such file or directory '{node_path_str}'.") 
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
    
    return "/" + "/".join(path_parts)

def help_command(command_name=None):
    if not command_name:
        print_to_terminal("Available commands. Type 'help <command>' for more info:")
        output = [f"  {cmd}" for cmd in sorted(COMMAND_HELP.keys())]
        print_to_terminal("\n".join(output))
    else:
        if command_name in COMMAND_HELP:
            print_to_terminal(COMMAND_HELP[command_name])
        else:
            print_to_terminal(f"Error: Unknown command '{command_name}'.")

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

    # parse input, split string into a list of words and convert to lower case 
    parts = command_input.split()
    command = parts[0].lower()
    
    # if block to validate and execute command
    if command == "exit":
        print_to_terminal("Exiting. (Reload the page to restart.)")
        input_el.disabled = True
    
    elif command == "ls":
        target_path = parts[1] if len(parts) > 1 else None
        ls_command(current_dir_id, target_path)
        
    elif command == "mkdir":
        if len(parts) > 1:
            mkdir_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: mkdir <path>")
    
    elif command == "cd":
        if len(parts) > 1:
            current_dir_id = cd_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: cd <path>")
    
    elif command == "touch":
        if len(parts) > 1:
            touch_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: touch <path>")

    elif command == "cat":
        if len(parts) > 1:
            cat_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: cat <path>")
    
    elif command == "write":
        if len(parts) < 3:
            print_to_terminal("Usage: write <path> <content...>")
        else:
            _parts = command_input.split(maxsplit=2)
            file_path = _parts[1]
            content = _parts[2]
            write_command(current_dir_id, file_path, content)
    
    elif command == "rm":
        if len(parts) > 1:
            rm_command(current_dir_id, parts[1])
        else:
            print_to_terminal("Usage: rm <path>")

    elif command == "pwd": 
        pwd_command(current_dir_id)

    elif command == "help":
        target_command = parts[1] if len(parts) > 1 else None
        help_command(target_command)

    else:
        print_to_terminal(f"Command not found: '{command}'")
    
    # Update the prompt for the next line
    if not input_el.disabled:
        prompt_el = document.querySelector("#prompt")
        prompt_el.innerText = get_prompt()

def main_setup():
    initialize_database()
    print_to_terminal("Welcome!")
    print_to_terminal("Commands: 'ls', 'mkdir', 'cd', 'touch', 'cat', 'write', 'rm', 'pwd', 'help', 'exit'.") 

    prompt_el = document.querySelector("#prompt")
    prompt_el.innerText = get_prompt()
    
    document.querySelector("#command-input").focus()

# main setup run
main_setup()