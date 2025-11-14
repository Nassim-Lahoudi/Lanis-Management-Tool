import tkinter as tk
import socket
import threading
import logging
from tkinter import messagebox, ttk
from lanisapi import LanisClient, LanisAccount
from lanisapi.exceptions import LoginPageRedirectError

# Logging to existing log file for simple diagnostics
logging.basicConfig(filename='html_logs.txt', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def lanis_client(school_id, name_lastname, password):
    client = LanisClient(LanisAccount(school_id, name_lastname, password))
    try:
        logging.info('Authenticating user %s@%s', name_lastname, school_id)
        # Initial authentication
        client.authenticate()

        # Try to get tasks. If the session has expired or Lanis redirected to
        # the login page, `LoginPageRedirectError` may be raised by the
        # underlying library. In that case try a single re-authentication
        # and one retry to avoid forcing the user to restart the app.
        try:
            tasks = client.get_tasks()
        except LoginPageRedirectError as e:
            logging.warning('Session may be expired: %s', e)
            # Attempt one re-authentication and retry
            try:
                logging.info('Attempting re-authentication for user %s@%s', name_lastname, school_id)
                client.authenticate()
                tasks = client.get_tasks()
            except LoginPageRedirectError as e2:
                logging.exception('Re-authentication failed: %s', e2)
                raise
        if isinstance(tasks, list) and tasks:
            message = f"Found {len(tasks)} tasks."
            logging.info(message)
            messagebox.showinfo("Tasks", message)
        else:
            logging.info('No tasks returned or unknown format')
            messagebox.showinfo("Tasks", "No tasks found or unknown format.")
    except LoginPageRedirectError as login_error:
        logging.exception('Lanis returned login page (session issue): %s', login_error)
        messagebox.showerror("Session Error", "Lanis returned the login page. Your session may have expired — please try logging in again.")
    except Exception as error:
        logging.exception('Error in Lanis client: %s', error)
        messagebox.showerror("Error", f"An error occurred while connecting: {error}")
    finally:
        try:
            client.close()
        except Exception:
            pass

def userinterface_window():
    window = tk.Tk()
    window.title('Lanis Management Tool')
    window.geometry('600x400')
    window.resizable(False, False)
    window.configure(bg='#F3F3F3')
    # Do not keep the window permanently on top

    show_password_var = tk.IntVar()

    def get_userdata():
        school_id = school_id_entry.get()
        name_lastname = name_lastname_entry.get()
        password = password_entry.get()

        # Input validation
        if not school_id.strip() or not name_lastname.strip() or not password:
            messagebox.showwarning('Warning', 'Please fill in all fields.')
            return

        # Start authentication in a background thread so the GUI doesn't block
        def auth_thread():
            try:
                lanis_client(school_id, name_lastname, password)
            except Exception as error:
                logging.exception('Error running lanis_client: %s', error)
                window.after(0, lambda: messagebox.showerror('Error', f'Login error: {error}'))

        threading.Thread(target=auth_thread, daemon=True).start()


    def show_connection_window():
        connection_window = tk.Toplevel(window)
        connection_window.title('Check Connection & User Information')
        connection_window.geometry('400x200')
        connection_window.resizable(False, False)
        connection_window.configure(bg='#F3F3F3')
        # connection_window.attributes('-topmost', True)
        connection_window.grab_set()

        tk.Label(connection_window, text="Check Internet Connection...", bg='#F3F3F3', font="Arial 10").pack(pady=5)
        internet_status_label = tk.Label(connection_window, text='', bg='#F3F3F3', font='Arial 13')
        internet_status_label.pack()

        tk.Label(connection_window, text="Check User information...", bg='#F3F3F3', font="Arial 10").pack(pady=5)
        userinfo_status_label = tk.Label(connection_window, text='', bg='#F3F3F3', font='Arial 13')
        userinfo_status_label.pack()

        progress = ttk.Progressbar(connection_window, orient="horizontal", length=300, mode="indeterminate")
        progress.pack(pady=10)
        progress.start(10)

        def check_internet_connection(host="8.8.8.8", port=53, timeout=3):
            def update_message(success):
                if success:
                    internet_status_label.config(text="Internet connection successful")
                    connection_window.after(800, check_user_information)
                else:
                    progress.stop()
                    internet_status_label.config(text="No internet connection")
                    messagebox.showerror('Error', 'No internet connection available.')

            def perform_check():
                try:
                    socket.setdefaulttimeout(timeout)
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.connect((host, port))
                        # Update GUI from main thread
                        connection_window.after(0, lambda: update_message(True))
                    finally:
                        s.close()
                except socket.error:
                    connection_window.after(0, lambda: update_message(False))

            # Start the network check in its own thread so it doesn't block the GUI
            threading.Thread(target=perform_check, daemon=True).start()

        def check_user_information():
            try:
                userinfo_status_label.config(text="Checking user information...")
                # get_userdata starts authentication in a background thread
                get_userdata()
                userinfo_status_label.config(text="User information check started")
            except Exception as error:
                userinfo_status_label.config(text="Error during check")
                logging.exception('Error in check_user_information: %s', error)
                messagebox.showerror("Error", f"An error occurred: {error}")
            finally:
                progress.stop()

        check_internet_connection()


    def show_password_function():
        password_entry.configure(show="" if show_password_var.get() else "*")

    def quit_function():
        if messagebox.askquestion('Warning', 'Are you sure?', icon='warning') == 'yes':
            window.quit()

    # window.protocol('WM_DELETE_WINDOW', quit_function)

    # Header
    tk.Label(window, text='Lanis Management Tool', bg='#F3F3F3', font='Arial 20 bold').pack(anchor='n', pady=20)

    # School ID
    tk.Label(window, text='School ID (1234):', font="Arial 9", bg='#F3F3F3').place(x=177, y=80)
    school_id_entry = tk.Entry(window, width=40)
    school_id_entry.place(x=180, y=110)

    # Username
    tk.Label(window, text='name.lastname (max.mustermann):', font="Arial 9", bg='#F3F3F3').place(x=177, y=140)
    name_lastname_entry = tk.Entry(window, width=40)
    name_lastname_entry.place(x=180, y=170)

    # Password
    tk.Label(window, text='Password:', font="Arial 9", bg='#F3F3F3').place(x=177, y=200)
    password_entry = tk.Entry(window, show='*', width=40)
    password_entry.place(x=180, y=230)

    # Show password checkbox
    tk.Checkbutton(window, text='Show Password', variable=show_password_var, command=show_password_function, bg='#F3F3F3').place(x=180, y=260)

    # Buttons
    login_button = tk.Button(window, text='Login', font="Arial 10 bold", cursor="hand2",bg="blue", fg="white", width=8, command=show_connection_window)
    login_button.place(x=180, y=290)

    tk.Button(window, text='Quit', font="Arial 10 bold", cursor="hand2",bg="red", fg="white", width=8, command=quit_function).place(x=350, y=290)

    window.mainloop()

userinterface_window()
