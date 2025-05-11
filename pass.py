#!/usr/bin/env python3
"""
pass.py - A Python implementation of the standard unix password manager

This script aims to provide the same functionality as the bash-based 'pass'
utility without external Python dependencies, making it more portable.
"""

import os
import sys
import subprocess
import getopt
import re
import glob
import shutil
import tempfile
import random
import string
import signal
import time
import threading

# Default configuration (can be overridden by environment variables)
PASSWORD_STORE_DIR = os.environ.get('PASSWORD_STORE_DIR', os.path.join(os.environ.get('HOME', ''), '.password-store'))
PASSWORD_STORE_GPG_OPTS = os.environ.get('PASSWORD_STORE_GPG_OPTS', '').split()
PASSWORD_STORE_X_SELECTION = os.environ.get('PASSWORD_STORE_X_SELECTION', 'clipboard')
PASSWORD_STORE_CLIP_TIME = int(os.environ.get('PASSWORD_STORE_CLIP_TIME', 45))
PASSWORD_STORE_UMASK = os.environ.get('PASSWORD_STORE_UMASK', '077')
PASSWORD_STORE_GENERATED_LENGTH = int(os.environ.get('PASSWORD_STORE_GENERATED_LENGTH', 25))
PASSWORD_STORE_CHARACTER_SET = os.environ.get('PASSWORD_STORE_CHARACTER_SET', string.punctuation + string.ascii_letters + string.digits)
PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS = os.environ.get('PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS', string.ascii_letters + string.digits)
PASSWORD_STORE_SIGNING_KEY = os.environ.get('PASSWORD_STORE_SIGNING_KEY', '')
PASSWORD_STORE_EXTENSIONS_DIR = os.environ.get('PASSWORD_STORE_EXTENSIONS_DIR', os.path.join(PASSWORD_STORE_DIR, '.extensions'))
PASSWORD_STORE_ENABLE_EXTENSIONS = os.environ.get('PASSWORD_STORE_ENABLE_EXTENSIONS', 'true').lower() == 'true'

# GPG command - prefer gpg2 if available
GPG = 'gpg2' if shutil.which('gpg2') else 'gpg'
GPG_OPTS = PASSWORD_STORE_GPG_OPTS + ['--quiet', '--yes', '--compress-algo=none', '--no-encrypt-to']

# Check if gpg-agent is available
if 'GPG_AGENT_INFO' in os.environ or GPG == 'gpg2':
    GPG_OPTS += ['--batch', '--use-agent']

class PassError(Exception):
    """Exception raised for password-store specific errors."""
    pass

def set_umask():
    """Set the umask based on the PASSWORD_STORE_UMASK environment variable."""
    os.umask(int(PASSWORD_STORE_UMASK, 8))

def die(message):
    """Print an error message and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

def check_sneaky_paths(*paths):
    """Check if paths contain sneaky path components like '../'."""
    for path in paths:
        if re.search(r'/\.\.$|\.\./|/\.\./', path) or path == '..':
            die("You've attempted to pass a sneaky path to pass. Go home.")

def is_git_repository(directory):
    """Check if the given directory is a git repository."""
    try:
        subprocess.run(
            ['git', '-C', directory, 'rev-parse', '--is-inside-work-tree'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def set_git_dir(path):
    """Find the nearest git directory for a given path."""
    git_dir = os.path.dirname(path)
    prefix = os.path.abspath(PASSWORD_STORE_DIR)
    
    while not os.path.isdir(git_dir) and git_dir.startswith(prefix):
        git_dir = os.path.dirname(git_dir)
    
    if not is_git_repository(git_dir):
        return None
    
    return git_dir

def git_add_file(git_dir, path, message):
    """Add a file to git and commit it with the given message."""
    if not git_dir:
        return

    try:
        subprocess.run(['git', '-C', git_dir, 'add', path], check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if there are changes to commit
        result = subprocess.run(['git', '-C', git_dir, 'status', '--porcelain', path], 
                               check=True, stdout=subprocess.PIPE, text=True)
        
        if not result.stdout:
            return  # No changes to commit
        
        # Check if commits should be signed
        sign = []
        try:
            signed = subprocess.run(
                ['git', '-C', git_dir, 'config', '--bool', '--get', 'pass.signcommits'],
                stdout=subprocess.PIPE, text=True, check=False
            )
            if signed.stdout.strip() == 'true':
                sign = ['-S']
        except subprocess.CalledProcessError:
            pass
            
        subprocess.run(['git', '-C', git_dir, 'commit'] + sign + ['-m', message], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}", file=sys.stderr)

def set_gpg_recipients(path=""):
    """Get the GPG recipients for the path."""
    recipients = []
    recipient_args = []
    
    # Check if PASSWORD_STORE_KEY is set
    store_key = os.environ.get('PASSWORD_STORE_KEY', '')
    if store_key:
        for gpg_id in store_key.split():
            recipient_args.extend(['-r', gpg_id])
            recipients.append(gpg_id)
        return recipients, recipient_args
    
    # Find the .gpg-id file
    current = os.path.join(PASSWORD_STORE_DIR, path)
    while current != PASSWORD_STORE_DIR and not os.path.isfile(os.path.join(current, '.gpg-id')):
        current = os.path.dirname(current)
    
    gpg_id_file = os.path.join(current, '.gpg-id')
    
    if not os.path.isfile(gpg_id_file):
        die("You must run:\n    pass init <gpg-id>\nbefore you may use the password store.")
    
    # Verify the .gpg-id file if needed
    if PASSWORD_STORE_SIGNING_KEY:
        verify_file(gpg_id_file)
    
    # Read recipients from .gpg-id file
    with open(gpg_id_file, 'r') as f:
        for line in f:
            gpg_id = line.split('#')[0].strip()  # Strip comments
            if gpg_id:
                recipient_args.extend(['-r', gpg_id])
                recipients.append(gpg_id)
    
    return recipients, recipient_args

def verify_file(path):
    """Verify a file's signature."""
    if not PASSWORD_STORE_SIGNING_KEY:
        return True
    
    if not os.path.isfile(f"{path}.sig"):
        die(f"Signature for {path} does not exist.")
    
    try:
        result = subprocess.run(
            [GPG] + GPG_OPTS + ['--verify', '--status-fd=1', f"{path}.sig", path],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False
        )
        
        valid_sigs = re.findall(r'\[GNUPG:\] VALIDSIG ([A-F0-9]{40}) .* ([A-F0-9]{40})', result.stdout)
        fingerprints = [sig[0] for sig in valid_sigs] + [sig[1] for sig in valid_sigs]
        
        # Check if any of the singing keys match
        for key in PASSWORD_STORE_SIGNING_KEY.split():
            if re.match(r'^[A-F0-9]{40}$', key) and key in fingerprints:
                return True
        
        die(f"Signature for {path} is invalid.")
    except subprocess.CalledProcessError:
        die(f"Could not verify the signature for {path}.")

def yesno(question):
    """Ask a yes/no question and return True if the answer is yes."""
    if not sys.stdin.isatty():
        return True
    
    response = input(f"{question} [y/N] ")
    return response.lower() in ('y', 'yes')

def pass_clip(content, name):
    """Copy content to the clipboard and clear after timeout."""
    # Determine clipboard command based on environment
    if 'WAYLAND_DISPLAY' in os.environ and shutil.which('wl-copy'):
        copy_cmd = ['wl-copy']
        paste_cmd = ['wl-paste', '-n']
        display_name = os.environ.get('WAYLAND_DISPLAY')
        
        if PASSWORD_STORE_X_SELECTION == 'primary':
            copy_cmd.append('--primary')
            paste_cmd.append('--primary')
    elif 'DISPLAY' in os.environ and shutil.which('xclip'):
        copy_cmd = ['xclip', '-selection', PASSWORD_STORE_X_SELECTION]
        paste_cmd = ['xclip', '-o', '-selection', PASSWORD_STORE_X_SELECTION]
        display_name = os.environ.get('DISPLAY')
    else:
        die("Error: No X11 or Wayland display and clipper detected")
    
    # Kill any existing sleep processes
    sleep_argv = f"password store sleep on display {display_name}"
    try:
        subprocess.run(['pkill', '-f', f"^{sleep_argv}"], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(0.5)
    except:
        pass
    
    # Store the original clipboard
    try:
        before = subprocess.run(paste_cmd, stdout=subprocess.PIPE, 
                               stderr=subprocess.DEVNULL, check=False).stdout
    except:
        before = b''
    
    # Copy the content to clipboard
    try:
        p = subprocess.Popen(copy_cmd, stdin=subprocess.PIPE)
        p.communicate(input=content.encode())
        if p.returncode != 0:
            die("Could not copy data to the clipboard")
    except Exception as e:
        die(f"Could not copy data to the clipboard: {e}")
    
    # Clear the clipboard after timeout
    def clear_clipboard():
        try:
            # Check if content is still in clipboard
            now = subprocess.run(paste_cmd, stdout=subprocess.PIPE, 
                                stderr=subprocess.DEVNULL, check=False).stdout
            
            if now != content.encode():
                # Something else has been copied, don't clear
                before = now
            
            # Try to clear clipboard history (KDE Klipper)
            try:
                subprocess.run(['qdbus', 'org.kde.klipper', '/klipper', 
                               'org.kde.klipper.klipper.clearClipboardHistory'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except:
                pass
            
            # Restore original clipboard
            p = subprocess.Popen(copy_cmd, stdin=subprocess.PIPE)
            p.communicate(input=before)
        except:
            pass
    
    print(f"Copied {name} to clipboard. Will clear in {PASSWORD_STORE_CLIP_TIME} seconds.")
    
    # Set up timer to clear clipboard
    timer = threading.Timer(PASSWORD_STORE_CLIP_TIME, clear_clipboard)
    timer.daemon = True
    timer.start()

def pass_qrcode(content, name):
    """Generate a QR code for the given content."""
    if not shutil.which('qrencode'):
        die("Error: qrencode is not installed.")
    
    if ('DISPLAY' in os.environ or 'WAYLAND_DISPLAY' in os.environ):
        if shutil.which('feh'):
            p1 = subprocess.Popen(['qrencode', '--size', '10', '-o', '-'], 
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['feh', '-x', '--title', f"pass: {name}", 
                                  '-g', '+200+200', '-'], stdin=p1.stdout)
            p1.stdin.write(content.encode())
            p1.stdin.close()
            p1.stdout.close()
            p2.wait()
            return
        elif shutil.which('gm'):
            p1 = subprocess.Popen(['qrencode', '--size', '10', '-o', '-'], 
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gm', 'display', '-title', f"pass: {name}", 
                                  '-geometry', '+200+200', '-'], stdin=p1.stdout)
            p1.stdin.write(content.encode())
            p1.stdin.close()
            p1.stdout.close()
            p2.wait()
            return
        elif shutil.which('display'):
            p1 = subprocess.Popen(['qrencode', '--size', '10', '-o', '-'], 
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['display', '-title', f"pass: {name}", 
                                  '-geometry', '+200+200', '-'], stdin=p1.stdout)
            p1.stdin.write(content.encode())
            p1.stdin.close()
            p1.stdout.close()
            p2.wait()
            return
    
    # Fallback to console output
    p = subprocess.Popen(['qrencode', '-t', 'utf8'], stdin=subprocess.PIPE)
    p.communicate(input=content.encode())

def cmd_version():
    """Show the version information."""
    print("""============================================
= pass: the standard unix password manager =
=                                          =
=              Python Edition              =
=                                          =
= Original:   Jason A. Donenfeld           =
=             Jason@zx2c4.com              =
=                                          =
= Python:     c4ffein                      =
=                                          =
= (Code actually written by Claude)        =
=                                          =
=      http://www.passwordstore.org/       =
============================================""")

def cmd_usage():
    """Show the usage information."""
    cmd_version()
    print()
    print(f"""Usage:
    {sys.argv[0]} init [--path=subfolder,-p subfolder] gpg-id...
        Initialize new password storage and use gpg-id for encryption.
        Selectively reencrypt existing passwords using new gpg-id.
    {sys.argv[0]} [ls] [subfolder]
        List passwords.
    {sys.argv[0]} find pass-names...
        List passwords that match pass-names.
    {sys.argv[0]} [show] [--clip[=line-number],-c[line-number]] pass-name
        Show existing password and optionally put it on the clipboard.
        If put on the clipboard, it will be cleared in {PASSWORD_STORE_CLIP_TIME} seconds.
    {sys.argv[0]} grep [GREPOPTIONS] search-string
        Search for password files containing search-string when decrypted.
    {sys.argv[0]} insert [--echo,-e | --multiline,-m] [--force,-f] pass-name
        Insert new password. Optionally, echo the password back to the console
        during entry. Or, optionally, the entry may be multiline. Prompt before
        overwriting existing password unless forced.
    {sys.argv[0]} edit pass-name
        Insert a new password or edit an existing password using ${EDITOR}.
    {sys.argv[0]} generate [--no-symbols,-n] [--clip,-c] [--in-place,-i | --force,-f] pass-name [pass-length]
        Generate a new password of pass-length (or {PASSWORD_STORE_GENERATED_LENGTH} if unspecified) with optionally no symbols.
        Optionally put it on the clipboard and clear board after {PASSWORD_STORE_CLIP_TIME} seconds.
        Prompt before overwriting existing password unless forced.
        Optionally replace only the first line of an existing file with a new password.
    {sys.argv[0]} rm [--recursive,-r] [--force,-f] pass-name
        Remove existing password or directory, optionally forcefully.
    {sys.argv[0]} mv [--force,-f] old-path new-path
        Renames or moves old-path to new-path, optionally forcefully, selectively reencrypting.
    {sys.argv[0]} cp [--force,-f] old-path new-path
        Copies old-path to new-path, optionally forcefully, selectively reencrypting.
    {sys.argv[0]} git git-command-args...
        If the password store is a git repository, execute a git command
        specified by git-command-args.
    {sys.argv[0]} help
        Show this text.
    {sys.argv[0]} version
        Show version information.

More information may be found in the pass(1) man page.""")

# Main command implementations will go here...

def cmd_init(argv):
    """Initialize a new password store."""
    # Parse arguments
    try:
        opts, args = getopt.getopt(argv, "p:", ["path="])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} init [--path=subfolder,-p subfolder] gpg-id...")
    
    id_path = ""
    
    for opt, arg in opts:
        if opt in ("-p", "--path"):
            id_path = arg
    
    if not args:
        die(f"Usage: {sys.argv[0]} init [--path=subfolder,-p subfolder] gpg-id...")
    
    # Check paths
    if id_path:
        check_sneaky_paths(id_path)
        full_path = os.path.join(PASSWORD_STORE_DIR, id_path)
        if os.path.exists(full_path) and not os.path.isdir(full_path):
            die(f"Error: {full_path} exists but is not a directory.")
    
    # Set up the .gpg-id file
    gpg_id_path = os.path.join(PASSWORD_STORE_DIR, id_path, ".gpg-id")
    git_dir = set_git_dir(gpg_id_path)
    
    # Handle removing GPG ID if no arguments provided
    if len(args) == 1 and not args[0]:
        if not os.path.isfile(gpg_id_path):
            die(f"Error: {gpg_id_path} does not exist and so cannot be removed.")
        
        try:
            os.remove(gpg_id_path)
            print(f"Removed {gpg_id_path}")
            
            if git_dir:
                subprocess.run(['git', '-C', git_dir, 'rm', '-qr', gpg_id_path], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                git_add_file(git_dir, gpg_id_path, f"Deinitialize {gpg_id_path}{' (' + id_path + ')' if id_path else ''}.")
            
            # Try to remove parent directories if empty
            try:
                os.removedirs(os.path.dirname(gpg_id_path))
            except:
                pass
            
        except Exception as e:
            die(f"Error removing {gpg_id_path}: {e}")
    else:
        # Create the directory and initialize with GPG IDs
        try:
            os.makedirs(os.path.dirname(gpg_id_path) if id_path else PASSWORD_STORE_DIR, exist_ok=True)
            with open(gpg_id_path, 'w') as f:
                f.write('\n'.join(args))
            
            id_print = ', '.join(args)
            print(f"Password store initialized for {id_print}{' (' + id_path + ')' if id_path else ''}")
            
            git_add_file(git_dir, gpg_id_path, f"Set GPG id to {id_print}{' (' + id_path + ')' if id_path else ''}.")
            
            # Sign the .gpg-id file if requested
            if PASSWORD_STORE_SIGNING_KEY:
                signing_keys = []
                for key in PASSWORD_STORE_SIGNING_KEY.split():
                    signing_keys.extend(['--default-key', key])
                
                subprocess.run([GPG] + GPG_OPTS + signing_keys + ['--detach-sign', gpg_id_path],
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                result = subprocess.run(
                    [GPG] + GPG_OPTS + ['--verify', '--status-fd=1', f"{gpg_id_path}.sig", gpg_id_path],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True
                )
                
                key = re.search(r'\[GNUPG:\] VALIDSIG [A-F0-9]{40} .* ([A-F0-9]{40})', result.stdout)
                if not key:
                    die("Signing of .gpg_id unsuccessful.")
                
                git_add_file(git_dir, f"{gpg_id_path}.sig", f"Signing new GPG id with {key.group(1)}.")
        
        except Exception as e:
            die(f"Error initializing password store: {e}")
        
        # Reencrypt the whole tree
        # This is a placeholder for the reencrypt_path function
        reencrypt_path(os.path.join(PASSWORD_STORE_DIR, id_path))
        git_add_file(git_dir, os.path.join(PASSWORD_STORE_DIR, id_path), 
                    f"Reencrypt password store using new GPG id {id_print}{' (' + id_path + ')' if id_path else ''}.")

def reencrypt_path(path):
    """Reencrypt all password files under the given path."""
    if not os.path.isdir(path):
        return
    
    prev_gpg_recipients = ""
    
    # Get gpg group information
    try:
        groups = subprocess.run(
            [GPG] + GPG_OPTS + ['--list-config', '--with-colons'],
            stdout=subprocess.PIPE, text=True, check=True
        ).stdout
        group_matches = re.findall(r"^cfg:group:.*", groups, re.MULTILINE)
    except:
        group_matches = []
    
    # Find all .gpg files
    for root, dirs, files in os.walk(path):
        # Skip .git and .extensions directories
        if '.git' in dirs:
            dirs.remove('.git')
        if '.extensions' in dirs:
            dirs.remove('.extensions')
        
        for file in files:
            if not file.endswith('.gpg'):
                continue
            
            # Skip symlinks
            file_path = os.path.join(root, file)
            if os.path.islink(file_path):
                continue
            
            # Get the directory relative to PASSWORD_STORE_DIR
            file_dir = os.path.dirname(file_path)
            relative_dir = os.path.relpath(file_dir, PASSWORD_STORE_DIR)
            if relative_dir == '.':
                relative_dir = ''
            
            # Display path for the user
            display_path = os.path.join(relative_dir, file[:-4])
            
            # Set GPG recipients for this directory
            recipients, recipient_args = set_gpg_recipients(relative_dir)
            
            if prev_gpg_recipients != ','.join(recipients):
                # Expand GPG groups
                i = 0
                while i < len(recipients):
                    for group in group_matches:
                        match = re.match(f"cfg:group:{re.escape(recipients[i])}:(.*)", group)
                        if match:
                            # Add group members
                            group_members = match.group(1).split(';')
                            recipients.extend(group_members)
                            del recipients[i]
                            i -= 1
                            break
                    i += 1
                
                # Get encryption subkeys
                try:
                    gpg_keys = subprocess.run(
                        [GPG] + GPG_OPTS + ['--list-keys', '--with-colons'] + recipients,
                        stdout=subprocess.PIPE, text=True, check=True
                    ).stdout
                    
                    encryption_keys = re.findall(
                        r"^sub:[^idr:]*:[^:]*:[^:]*:([^:]*):.*:[^:]*:[^:]*:[^:]*:[^:]*:[^:]*:[a-zA-Z]*e[a-zA-Z]*:",
                        gpg_keys, re.MULTILINE
                    )
                    encryption_keys.sort()
                except:
                    encryption_keys = []
            
            # Get the current keys for this file
            try:
                current_keys = subprocess.run(
                    [GPG] + GPG_OPTS + ['-v', '--no-secmem-warning', '--no-permission-warning', 
                                         '--decrypt', '--list-only', '--keyid-format', 'long', file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
                ).stderr
                
                current_key_list = re.findall(r"public key is ([A-F0-9]+)", current_keys)
                current_key_list.sort()
            except:
                current_key_list = []
            
            if ','.join(encryption_keys) != ','.join(current_key_list):
                print(f"{display_path}: reencrypting to {' '.join(encryption_keys)}")
                
                # Create a temporary file
                temp_file = f"{file_path}.tmp.{random.randint(1000000, 9999999)}.--"
                
                try:
                    # Decrypt and re-encrypt
                    decrypted = subprocess.run(
                        [GPG] + GPG_OPTS + ['-d', file_path],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                    ).stdout
                    
                    subprocess.run(
                        [GPG] + GPG_OPTS + ['-e'] + recipient_args + ['-o', temp_file],
                        input=decrypted, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    
                    # Replace the original file
                    shutil.move(temp_file, file_path)
                    
                except Exception as e:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    print(f"Error reencrypting {display_path}: {e}", file=sys.stderr)
            
            prev_gpg_recipients = ','.join(recipients)

def cmd_show(argv):
    """Show a password or list passwords."""
    # Parse arguments
    clip = 0
    qrcode_mode = 0
    selected_line = 1
    
    try:
        opts, args = getopt.getopt(argv, "c::q::", ["clip=", "clip", "qrcode=", "qrcode"])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} show [--clip[=line-number],-c[line-number]] [--qrcode[=line-number],-q[line-number]] [pass-name]")
    
    for opt, arg in opts:
        if opt in ("-c", "--clip"):
            clip = 1
            if arg:
                selected_line = arg
        elif opt in ("-q", "--qrcode"):
            qrcode_mode = 1
            if arg:
                selected_line = arg
    
    if clip and qrcode_mode:
        die(f"Usage: {sys.argv[0]} show [--clip[=line-number],-c[line-number]] [--qrcode[=line-number],-q[line-number]] [pass-name]")
    
    # Convert selected_line to int
    try:
        selected_line = int(selected_line)
    except ValueError:
        die(f"Clip location '{selected_line}' is not a number.")
    
    # Get path from args
    path = args[0] if args else ""
    
    # Check for sneaky paths
    check_sneaky_paths(path)
    
    # Construct the full path to the password file
    passfile = os.path.join(PASSWORD_STORE_DIR, path + ".gpg")
    
    if os.path.isfile(passfile):
        # Show the password
        if clip == 0 and qrcode_mode == 0:
            try:
                # Decrypt the password file
                result = subprocess.run(
                    [GPG] + GPG_OPTS + ['-d', passfile],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )
                print(result.stdout.decode())
            except subprocess.CalledProcessError as e:
                die(f"Failed to decrypt {path}: {e}")
        else:
            try:
                # Decrypt the password file and get the specified line
                result = subprocess.run(
                    [GPG] + GPG_OPTS + ['-d', passfile],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )
                
                lines = result.stdout.decode().splitlines()
                if selected_line > len(lines):
                    die(f"There is no password to put on the clipboard at line {selected_line}.")
                
                # Get the selected line (1-indexed)
                pass_line = lines[selected_line - 1]
                
                if not pass_line:
                    die(f"There is no password to put on the clipboard at line {selected_line}.")
                
                # Copy to clipboard or show as QR code
                if clip:
                    pass_clip(pass_line, path)
                elif qrcode_mode:
                    pass_qrcode(pass_line, path)
            except subprocess.CalledProcessError as e:
                die(f"Failed to decrypt {path}: {e}")
    elif os.path.isdir(os.path.join(PASSWORD_STORE_DIR, path)):
        # List passwords in the directory
        if not path:
            print("Password Store")
        else:
            print(path.rstrip('/'))
        
        # Use 'tree' command to list the passwords
        try:
            store_path = os.path.join(PASSWORD_STORE_DIR, path)
            
            # Run tree command
            tree_cmd = ['tree', '-N', '-C', '-l', '--noreport', store_path]
            tree_output = subprocess.run(
                tree_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
            ).stdout
            
            # Process and print tree output
            lines = tree_output.splitlines()
            if len(lines) > 1:
                for line in lines[1:]:  # Skip the first line which is the directory name
                    # Remove .gpg extension visually
                    print(re.sub(r'\.gpg(\x1B\[[0-9]+m)?( ->|$)', r'\1\2', line))
        except subprocess.CalledProcessError as e:
            # Fallback if tree command fails
            print(f"Error running tree: {e}", file=sys.stderr)
            print("Contents:")
            for root, dirs, files in os.walk(os.path.join(PASSWORD_STORE_DIR, path)):
                rel_root = os.path.relpath(root, os.path.join(PASSWORD_STORE_DIR, path))
                if rel_root != '.':
                    print(f"└── {rel_root}")
                
                for f in sorted(files):
                    if f.endswith('.gpg'):
                        print(f"    └── {f[:-4]}")
    elif not path:
        die("Error: password store is empty. Try \"pass init\".")
    else:
        die(f"Error: {path} is not in the password store.")

def cmd_find(argv):
    """Find passwords in the password store."""
    if not argv:
        die(f"Usage: {sys.argv[0]} find pass-names...")
    
    # Print search terms
    print(f"Search Terms: {', '.join(argv)}")
    
    # Create a glob pattern for tree command
    patterns = ['*' + term + '*' for term in argv]
    pattern_arg = '|'.join(patterns)
    
    try:
        # Use tree command to find matching password files
        tree_cmd = ['tree', '-N', '-C', '-l', '--noreport', '-P', pattern_arg, 
                    '--prune', '--matchdirs', '--ignore-case', PASSWORD_STORE_DIR]
        
        tree_output = subprocess.run(
            tree_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        ).stdout
        
        # Process and print tree output
        lines = tree_output.splitlines()
        if len(lines) > 1:
            for line in lines[1:]:  # Skip the first line which is the directory name
                # Remove .gpg extension visually
                print(re.sub(r'\.gpg(\x1B\[[0-9]+m)?( ->|$)', r'\1\2', line))
    except subprocess.CalledProcessError as e:
        # Fallback if tree command fails
        print(f"Error running tree search: {e}", file=sys.stderr)
        
        # Manual search through the password store
        found = False
        patterns = [re.compile(re.escape(term), re.IGNORECASE) for term in argv]
        
        for root, dirs, files in os.walk(PASSWORD_STORE_DIR):
            rel_root = os.path.relpath(root, PASSWORD_STORE_DIR)
            
            # Check if directory name matches any pattern
            dir_match = any(pattern.search(os.path.basename(rel_root)) for pattern in patterns)
            
            # Filter files that match or are in matching directories
            matching_files = []
            for f in files:
                if f.endswith('.gpg'):
                    name = f[:-4]
                    if dir_match or any(pattern.search(name) for pattern in patterns):
                        matching_files.append(name)
            
            if matching_files:
                found = True
                if rel_root != '.':
                    print(f"{rel_root}/")
                for name in sorted(matching_files):
                    print(f"└── {name}")
        
        if not found:
            print("No matching passwords found.")

def cmd_grep(argv):
    """Search for pattern in decrypted password files."""
    if not argv:
        die(f"Usage: {sys.argv[0]} grep [GREPOPTIONS] search-string")
    
    # Find all .gpg files and grep through their decrypted content
    for root, dirs, files in os.walk(PASSWORD_STORE_DIR):
        # Skip .git and .extensions directories
        if '.git' in dirs:
            dirs.remove('.git')
        if '.extensions' in dirs:
            dirs.remove('.extensions')
        
        for file in files:
            if not file.endswith('.gpg'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                # Decrypt the file
                decrypted = subprocess.run(
                    [GPG] + GPG_OPTS + ['-d', file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
                ).stdout.decode()
                
                # Search for pattern using grep
                try:
                    grep_result = subprocess.run(
                        ['grep', '--color=always'] + argv,
                        input=decrypted.encode(), stdout=subprocess.PIPE, text=True, check=False
                    )
                    
                    # If grep found matches
                    if grep_result.returncode == 0:
                        # Get relative path for display
                        rel_path = os.path.relpath(file_path, PASSWORD_STORE_DIR)
                        rel_path = rel_path[:-4]  # Remove .gpg extension
                        
                        # Split path into directory and filename
                        rel_dir = os.path.dirname(rel_path)
                        rel_file = os.path.basename(rel_path)
                        
                        if rel_dir:
                            print(f"\033[94m{rel_dir}/\033[1m{rel_file}\033[0m:")
                        else:
                            print(f"\033[94m\033[1m{rel_file}\033[0m:")
                            
                        print(grep_result.stdout)
                except:
                    # Handle error in grep command
                    pass
            except:
                # Skip files that can't be decrypted
                pass

def cmd_insert(argv):
    """Insert a new password."""
    # Parse arguments
    multiline = 0
    noecho = 1
    force = 0
    
    try:
        opts, args = getopt.getopt(argv, "mef", ["multiline", "echo", "force"])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} insert [--echo,-e | --multiline,-m] [--force,-f] pass-name")
    
    for opt, arg in opts:
        if opt in ("-m", "--multiline"):
            multiline = 1
        elif opt in ("-e", "--echo"):
            noecho = 0
        elif opt in ("-f", "--force"):
            force = 1
    
    if multiline and noecho == 0:
        die(f"Usage: {sys.argv[0]} insert [--echo,-e | --multiline,-m] [--force,-f] pass-name")
    
    if len(args) != 1:
        die(f"Usage: {sys.argv[0]} insert [--echo,-e | --multiline,-m] [--force,-f] pass-name")
    
    path = args[0].rstrip('/')
    check_sneaky_paths(path)
    
    passfile = os.path.join(PASSWORD_STORE_DIR, path + ".gpg")
    git_dir = set_git_dir(passfile)
    
    # Check if the file already exists
    if force == 0 and os.path.exists(passfile):
        if not yesno(f"An entry already exists for {path}. Overwrite it?"):
            sys.exit(1)
    
    # Create the parent directory if it doesn't exist
    os.makedirs(os.path.dirname(passfile), exist_ok=True)
    
    # Set up GPG recipients
    recipients, recipient_args = set_gpg_recipients(os.path.dirname(path))
    
    if multiline:
        # Read multiline input
        print(f"Enter contents of {path} and press Ctrl+D when finished:")
        print()
        password = sys.stdin.read()
    else:
        # Read password input
        if noecho:
            import getpass
            
            while True:
                password = getpass.getpass(f"Enter password for {path}: ")
                password_confirm = getpass.getpass(f"Retype password for {path}: ")
                
                if password == password_confirm:
                    break
                else:
                    print("Error: the entered passwords do not match.")
                    if not yesno("Try again?"):
                        sys.exit(1)
        else:
            password = input(f"Enter password for {path}: ")
    
    # Encrypt the password
    try:
        encrypt_cmd = [GPG] + GPG_OPTS + ['-e'] + recipient_args
        process = subprocess.Popen(
            encrypt_cmd + ['-o', passfile],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        process.communicate(input=password.encode())
        
        if process.returncode != 0:
            die("Password encryption aborted.")
    except Exception as e:
        die(f"Password encryption failed: {e}")
    
    # Add to git if needed
    git_add_file(git_dir, passfile, f"Add given password for {path} to store.")

def cmd_edit(argv):
    """Edit a password using an editor."""
    if len(argv) != 1:
        die(f"Usage: {sys.argv[0]} edit pass-name")
    
    path = argv[0].rstrip('/')
    check_sneaky_paths(path)
    
    mkdir_dir = os.path.join(PASSWORD_STORE_DIR, os.path.dirname(path))
    os.makedirs(mkdir_dir, exist_ok=True)
    
    # Set up GPG recipients
    recipients, recipient_args = set_gpg_recipients(os.path.dirname(path))
    
    passfile = os.path.join(PASSWORD_STORE_DIR, path + ".gpg")
    git_dir = set_git_dir(passfile)
    
    # Create a temporary directory
    secure_tmpdir = None
    shred_cmd = 'shred -f -z'
    
    if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK | os.X_OK):
        # Use /dev/shm for secure temporary storage
        secure_tmpdir = tempfile.mkdtemp(prefix=f"{os.path.basename(sys.argv[0])}.", dir='/dev/shm')
    else:
        # Fall back to normal tmp directory with warning
        if yesno("""Your system does not have /dev/shm, which means that it may
be difficult to entirely erase the temporary non-encrypted
password file after editing.

Are you sure you would like to continue?"""):
            secure_tmpdir = tempfile.mkdtemp(prefix=f"{os.path.basename(sys.argv[0])}.")
        else:
            sys.exit(1)
    
    # Create temporary file path
    tmp_file = os.path.join(secure_tmpdir, f"{os.path.basename(path)}.txt")
    
    try:
        # Check if the password file exists
        action = "Add"
        if os.path.isfile(passfile):
            action = "Edit"
            try:
                # Decrypt the existing password to the temporary file
                subprocess.run(
                    [GPG] + GPG_OPTS + ['-d', '-o', tmp_file, passfile],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError:
                # Clean up
                if os.path.isdir('/dev/shm'):
                    # Just remove the directory
                    shutil.rmtree(secure_tmpdir)
                else:
                    # Shred files first
                    for root, dirs, files in os.walk(secure_tmpdir):
                        for f in files:
                            file_path = os.path.join(root, f)
                            subprocess.run(shred_cmd.split() + [file_path], check=False)
                    shutil.rmtree(secure_tmpdir)
                sys.exit(1)
        
        # Get editor command
        editor = os.environ.get('EDITOR', 'vi')
        
        # Open editor
        try:
            subprocess.run([editor, tmp_file], check=True)
        except subprocess.CalledProcessError:
            die("Editor returned an error.")
        
        # Check if the temporary file exists
        if not os.path.isfile(tmp_file):
            die("New password not saved.")
        
        # Check if the password was changed
        if action == "Edit":
            old_sum = subprocess.run(
                ['sha1sum', passfile], stdout=subprocess.PIPE, text=True, check=True
            ).stdout.split()[0]
            
            new_sum = subprocess.run(
                ['sha1sum', tmp_file], stdout=subprocess.PIPE, text=True, check=True
            ).stdout.split()[0]
            
            if old_sum == new_sum:
                print("Password unchanged.")
                # Clean up and exit
                if os.path.isdir('/dev/shm'):
                    shutil.rmtree(secure_tmpdir)
                else:
                    for root, dirs, files in os.walk(secure_tmpdir):
                        for f in files:
                            file_path = os.path.join(root, f)
                            subprocess.run(shred_cmd.split() + [file_path], check=False)
                    shutil.rmtree(secure_tmpdir)
                return
        
        # Encrypt the edited password
        while True:
            try:
                encrypt_proc = subprocess.run(
                    [GPG] + GPG_OPTS + ['-e'] + recipient_args + ['-o', passfile, tmp_file],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                break
            except subprocess.CalledProcessError:
                if not yesno("GPG encryption failed. Would you like to try again?"):
                    die("Password encryption aborted.")
        
        # Add to git if needed
        git_add_file(git_dir, passfile, f"{action} password for {path} using {editor}.")
        
    finally:
        # Clean up
        if secure_tmpdir and os.path.exists(secure_tmpdir):
            if os.path.isdir('/dev/shm'):
                # Just remove the directory
                shutil.rmtree(secure_tmpdir)
            else:
                # Shred files first
                for root, dirs, files in os.walk(secure_tmpdir):
                    for f in files:
                        file_path = os.path.join(root, f)
                        subprocess.run(shred_cmd.split() + [file_path], check=False)
                shutil.rmtree(secure_tmpdir)

def cmd_generate(argv):
    """Generate a new password."""
    # Parse arguments
    noSymbols = False
    clip = 0
    force = 0
    inPlace = 0
    qrcode_mode = 0
    
    try:
        opts, args = getopt.getopt(argv, "nqcif", ["no-symbols", "qrcode", "clip", "in-place", "force"])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} generate [--no-symbols,-n] [--clip,-c] [--qrcode,-q] [--in-place,-i | --force,-f] pass-name [pass-length]")
    
    for opt, arg in opts:
        if opt in ("-n", "--no-symbols"):
            noSymbols = True
        elif opt in ("-q", "--qrcode"):
            qrcode_mode = 1
        elif opt in ("-c", "--clip"):
            clip = 1
        elif opt in ("-f", "--force"):
            force = 1
        elif opt in ("-i", "--in-place"):
            inPlace = 1
    
    # Both force and in-place can't be specified at the same time
    if force and inPlace:
        die(f"Usage: {sys.argv[0]} generate [--no-symbols,-n] [--clip,-c] [--qrcode,-q] [--in-place,-i | --force,-f] pass-name [pass-length]")
    
    # Both qrcode and clip can't be specified at the same time
    if qrcode_mode and clip:
        die(f"Usage: {sys.argv[0]} generate [--no-symbols,-n] [--clip,-c] [--qrcode,-q] [--in-place,-i | --force,-f] pass-name [pass-length]")
    
    # Need either 1 or 2 arguments
    if len(args) < 1 or len(args) > 2:
        die(f"Usage: {sys.argv[0]} generate [--no-symbols,-n] [--clip,-c] [--qrcode,-q] [--in-place,-i | --force,-f] pass-name [pass-length]")
    
    path = args[0].rstrip('/')
    check_sneaky_paths(path)
    
    # Get password length
    length = PASSWORD_STORE_GENERATED_LENGTH
    if len(args) > 1:
        try:
            length = int(args[1])
        except ValueError:
            die(f"Error: pass-length \"{args[1]}\" must be a number.")
    
    if length <= 0:
        die("Error: pass-length must be greater than zero.")
    
    # Set character set
    characters = PASSWORD_STORE_CHARACTER_SET if not noSymbols else PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS
    
    # Create directory structure
    mkdir_dir = os.path.join(PASSWORD_STORE_DIR, os.path.dirname(path))
    os.makedirs(mkdir_dir, exist_ok=True)
    
    # Set up GPG recipients
    recipients, recipient_args = set_gpg_recipients(os.path.dirname(path))
    
    passfile = os.path.join(PASSWORD_STORE_DIR, path + ".gpg")
    git_dir = set_git_dir(passfile)
    
    # Check if the file already exists
    if inPlace == 0 and force == 0 and os.path.exists(passfile):
        if not yesno(f"An entry already exists for {path}. Overwrite it?"):
            sys.exit(1)
    
    # Generate random password
    password = ''.join(random.choice(characters) for _ in range(length))
    
    if inPlace == 0:
        # Create a new password file
        try:
            encrypt_proc = subprocess.run(
                [GPG] + GPG_OPTS + ['-e'] + recipient_args + ['-o', passfile],
                input=password.encode(), check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            die("Password encryption aborted.")
    else:
        # Replace first line of existing file
        temp_file = f"{passfile}.tmp.{random.randint(1000000, 9999999)}.--"
        
        try:
            # Get the existing content without the first line
            result = subprocess.run(
                [GPG] + GPG_OPTS + ['-d', passfile],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            content = result.stdout.decode().splitlines()
            
            # Create new content with the new password as the first line
            new_content = password + '\n'
            if len(content) > 1:
                new_content += '\n'.join(content[1:])
            
            # Encrypt to temporary file
            encrypt_proc = subprocess.run(
                [GPG] + GPG_OPTS + ['-e'] + recipient_args + ['-o', temp_file],
                input=new_content.encode(), check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            
            # Replace the original file
            shutil.move(temp_file, passfile)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            die(f"Could not reencrypt new password: {e}")
    
    # Add to git if needed
    verb = "Add" if not inPlace else "Replace"
    git_add_file(git_dir, passfile, f"{verb} generated password for {path}.")
    
    # Output the password
    if clip:
        pass_clip(password, path)
    elif qrcode_mode:
        pass_qrcode(password, path)
    else:
        print(f"\033[1mThe generated password for \033[4m{path}\033[24m is:\033[0m")
        print(f"\033[1m\033[93m{password}\033[0m")

def cmd_delete(argv):
    """Remove a password or directory from the store."""
    # Parse arguments
    recursive = False
    force = 0
    
    try:
        opts, args = getopt.getopt(argv, "rf", ["recursive", "force"])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} rm [--recursive,-r] [--force,-f] pass-name")
    
    for opt, arg in opts:
        if opt in ("-r", "--recursive"):
            recursive = True
        elif opt in ("-f", "--force"):
            force = 1
    
    if len(args) != 1:
        die(f"Usage: {sys.argv[0]} rm [--recursive,-r] [--force,-f] pass-name")
    
    path = args[0]
    check_sneaky_paths(path)
    
    passdir = os.path.join(PASSWORD_STORE_DIR, path)
    passfile = os.path.join(PASSWORD_STORE_DIR, path + ".gpg")
    
    # Check if it's a directory with trailing slash or not a file
    if (os.path.isfile(passfile) and os.path.isdir(passdir) and path.endswith('/')) or not os.path.isfile(passfile):
        passfile = passdir
    
    # Check if the path exists
    if not os.path.exists(passfile):
        die(f"Error: {path} is not in the password store.")
    
    git_dir = set_git_dir(passfile)
    
    # Confirm deletion
    if force == 0:
        if not yesno(f"Are you sure you would like to delete {path}?"):
            sys.exit(1)
    
    # Remove the file or directory
    try:
        if os.path.isdir(passfile):
            if not recursive:
                die(f"Error: {path} is a directory, use -r to remove recursively.")
            shutil.rmtree(passfile)
        else:
            os.remove(passfile)
            
        # Remove from git if needed
        if git_dir and not os.path.exists(passfile):
            subprocess.run(['git', '-C', git_dir, 'rm', '-qr', passfile],
                          check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git_add_file(git_dir, passfile, f"Remove {path} from store.")
        
        # Try to remove empty parent directories
        try:
            os.removedirs(os.path.dirname(passfile))
        except:
            pass
            
    except Exception as e:
        die(f"Error removing {path}: {e}")

def cmd_copy_move(command, argv):
    """Copy or move a password or directory."""
    # Parse arguments
    force = 0
    
    try:
        opts, args = getopt.getopt(argv, "f", ["force"])
    except getopt.GetoptError as e:
        die(f"{e}\nUsage: {sys.argv[0]} {command} [--force,-f] old-path new-path")
    
    for opt, arg in opts:
        if opt in ("-f", "--force"):
            force = 1
    
    if len(args) != 2:
        die(f"Usage: {sys.argv[0]} {command} [--force,-f] old-path new-path")
    
    old_path, new_path = args
    check_sneaky_paths(old_path, new_path)
    
    old_path_full = os.path.join(PASSWORD_STORE_DIR, old_path)
    old_dir = old_path_full
    
    # Determine if this is a file or directory (with or without .gpg extension)
    if not (os.path.isfile(old_path_full + ".gpg") and os.path.isdir(old_path_full) and old_path.endswith('/') or 
           not os.path.isfile(old_path_full + ".gpg")):
        old_dir = os.path.dirname(old_path_full)
        old_path_full = old_path_full + ".gpg"
    
    if not os.path.exists(old_path_full):
        die(f"Error: {old_path} is not in the password store.")
    
    # Create the destination directory
    new_path_full = os.path.join(PASSWORD_STORE_DIR, new_path)
    os.makedirs(os.path.dirname(new_path_full), exist_ok=True)
    
    # Determine if the destination is a directory
    if os.path.isdir(old_path_full) or os.path.isdir(new_path_full) or new_path.endswith('/'):
        if not os.path.isdir(new_path_full):
            os.makedirs(new_path_full)
    else:
        new_path_full = new_path_full + ".gpg"
    
    # Determine copy mode (interactive or force)
    interactive = "-i" if force == 0 and sys.stdin.isatty() else "-f"
    
    # Set git directory for operations
    git_dir = set_git_dir(new_path_full)
    
    if command == "move":
        # Move operation
        try:
            if os.path.isdir(old_path_full):
                cmd = ["cp", "-r"] + ([interactive] if not force else []) + [old_path_full, new_path_full]
                subprocess.run(cmd, check=True)
                shutil.rmtree(old_path_full)
            else:
                cmd = ["cp"] + ([interactive] if not force else []) + [old_path_full, new_path_full]
                subprocess.run(cmd, check=True)
                os.remove(old_path_full)
                
            # Reencrypt if needed
            if os.path.exists(new_path_full):
                reencrypt_path(new_path_full)
            
            # Git operations
            if git_dir and not os.path.exists(old_path_full):
                subprocess.run(['git', '-C', git_dir, 'rm', '-qr', old_path_full],
                              check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                git_add_file(git_dir, new_path_full, f"Rename {old_path} to {new_path}.")
                
                # Remove old file from git
                if subprocess.run(['git', '-C', git_dir, 'status', '--porcelain', old_path_full],
                                 stdout=subprocess.PIPE).stdout:
                    git_add_file(git_dir, old_path_full, f"Remove {old_path}.")
            
            # Try to remove empty parent directories
            try:
                os.removedirs(old_dir)
            except:
                pass
                
        except Exception as e:
            die(f"Error moving {old_path} to {new_path}: {e}")
            
    else:
        # Copy operation
        try:
            if os.path.isdir(old_path_full):
                cmd = ["cp", "-r"] + ([interactive] if not force else []) + [old_path_full, new_path_full]
            else:
                cmd = ["cp"] + ([interactive] if not force else []) + [old_path_full, new_path_full]
                
            subprocess.run(cmd, check=True)
            
            # Reencrypt if needed
            if os.path.exists(new_path_full):
                reencrypt_path(new_path_full)
            
            # Git operations
            git_add_file(git_dir, new_path_full, f"Copy {old_path} to {new_path}.")
                
        except Exception as e:
            die(f"Error copying {old_path} to {new_path}: {e}")

def cmd_git(argv):
    """Execute git commands on the password store."""
    git_dir = set_git_dir(os.path.join(PASSWORD_STORE_DIR, "/"))
    
    if argv and argv[0] == "init":
        # Initialize a new git repository
        git_dir = PASSWORD_STORE_DIR
        try:
            subprocess.run(['git', '-C', git_dir, 'init'] + argv[1:],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git_add_file(git_dir, PASSWORD_STORE_DIR, "Add current contents of password store.")
            
            # Add .gitattributes file
            with open(os.path.join(PASSWORD_STORE_DIR, ".gitattributes"), 'w') as f:
                f.write('*.gpg diff=gpg\n')
            
            git_add_file(git_dir, os.path.join(PASSWORD_STORE_DIR, ".gitattributes"), 
                        "Configure git repository for gpg file diff.")
            
            # Set git configuration for diffing GPG files
            subprocess.run(['git', '-C', git_dir, 'config', '--local', 'diff.gpg.binary', 'true'],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Create a command that includes all GPG options
            gpg_opts_str = ' '.join(GPG_OPTS)
            subprocess.run(['git', '-C', git_dir, 'config', '--local', 'diff.gpg.textconv', 
                           f"{GPG} -d {gpg_opts_str}"],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        except Exception as e:
            die(f"Error initializing git repository: {e}")
    elif git_dir:
        # Create secure temporary directory for git operations
        secure_tmpdir = tempfile.mkdtemp(prefix=f"{os.path.basename(sys.argv[0])}.", 
                                        dir='/dev/shm' if os.path.isdir('/dev/shm') else None)
        try:
            # Set TMPDIR environment variable for git
            env = os.environ.copy()
            env['TMPDIR'] = secure_tmpdir
            
            # Run the git command
            subprocess.run(['git', '-C', git_dir] + argv, env=env, check=False)
        finally:
            # Clean up temporary directory
            if os.path.exists(secure_tmpdir):
                shutil.rmtree(secure_tmpdir)
    else:
        die("Error: the password store is not a git repository. Try \"pass git init\".")

def main():
    """Main function."""
    set_umask()
    
    if len(sys.argv) < 2 or sys.argv[1] == "help" or sys.argv[1] == "--help":
        cmd_usage()
        return 0
    
    command = sys.argv[1]
    
    # Execute the corresponding command
    if command == "version" or command == "--version":
        cmd_version()
    elif command == "init":
        cmd_init(sys.argv[2:])
    elif command == "ls" or command == "list" or command == "show":
        cmd_show(sys.argv[2:])
    elif command == "find" or command == "search":
        cmd_find(sys.argv[2:])
    elif command == "grep":
        cmd_grep(sys.argv[2:])
    elif command == "insert" or command == "add":
        cmd_insert(sys.argv[2:])
    elif command == "edit":
        cmd_edit(sys.argv[2:])
    elif command == "generate":
        cmd_generate(sys.argv[2:])
    elif command == "rm" or command == "remove" or command == "delete":
        cmd_delete(sys.argv[2:])
    elif command == "mv" or command == "rename":
        cmd_copy_move("move", sys.argv[2:])
    elif command == "cp" or command == "copy":
        cmd_copy_move("copy", sys.argv[2:])
    elif command == "git":
        cmd_git(sys.argv[2:])
    else:
        # Not found - Use show command by default
        cmd_show([command] + sys.argv[2:])
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except PassError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        sys.exit(130)