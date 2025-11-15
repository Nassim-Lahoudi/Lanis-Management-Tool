import tkinter as tk  # import tkinter GUI library and alias it as tk for convenience
import socket  # import socket module used for network connection checks
import threading  # import threading to run background tasks without blocking the GUI
import logging  # import logging to record events and errors to a file
from tkinter import messagebox, ttk  # import messagebox for dialogs and ttk for themed widgets
from lanisapi import LanisClient, LanisAccount  # import Lanis API client classes for authentication and actions
from lanisapi.exceptions import LoginPageRedirectError  # import the specific exception raised when Lanis redirects to the login page

# Configure basic logging to a file with timestamped entries for diagnostics
logging.basicConfig(filename='html_logs.txt', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def lanis_client(school_id, name_lastname, password):  # define a function to authenticate and fetch tasks from Lanis
    client = LanisClient(LanisAccount(school_id, name_lastname, password))  # create a LanisClient using provided credentials
    try:
        logging.info('Authenticating user %s@%s', name_lastname, school_id)  # log attempt to authenticate
        # Initial authentication
        client.authenticate()  # perform the initial authentication call against Lanis

        # Try to get tasks. If the session has expired or Lanis redirected to
        # the login page, `LoginPageRedirectError` may be raised by the
        # underlying library. In that case try a single re-authentication
        # and one retry to avoid forcing the user to restart the app.
        try:
            tasks = client.get_tasks()  # request tasks from the authenticated session
        except LoginPageRedirectError as e:
            logging.warning('Session may be expired: %s', e)  # warn that the login page was returned and session may be expired
            # Attempt one re-authentication and retry
            try:
                logging.info('Attempting re-authentication for user %s@%s', name_lastname, school_id)  # log re-authentication attempt
                client.authenticate()  # re-authenticate once
                tasks = client.get_tasks()  # retry fetching tasks after re-authentication
            except LoginPageRedirectError as e2:
                logging.exception('Re-authentication failed: %s', e2)  # log if re-authentication also failed
                raise  # re-raise the exception to be handled by outer handler
        if isinstance(tasks, list) and tasks:  # check if tasks is a non-empty list
            message = f"Found {len(tasks)} tasks."  # prepare a user-facing message with the number of tasks
            logging.info(message)  # log the message about found tasks
            messagebox.showinfo("Tasks", message)  # show an informational dialog with the number of tasks
        else:
            logging.info('No tasks returned or unknown format')  # log that tasks were empty or had unexpected format
            messagebox.showinfo("Tasks", "No tasks found or unknown format.")  # inform the user no tasks were found
    except LoginPageRedirectError as login_error:
        logging.exception('Lanis returned login page (session issue): %s', login_error)  # log the login redirect as an exception
        messagebox.showerror("Session Error", "Lanis returned the login page. Your session may have expired — please try logging in again.")  # show a clear session error to the user
    except Exception as error:
        logging.exception('Error in Lanis client: %s', error)  # log any other unexpected exceptions with stack trace
        messagebox.showerror("Error", f"An error occurred while connecting: {error}")  # display a generic connection error to the user
    finally:
        try:
            client.close()  # close the Lanis client to release resources
        except Exception:
            pass  # ignore errors during close to avoid masking original exceptions


def userinterface_window():  # define and build the main GUI window
    window = tk.Tk()  # create the main Tkinter window instance
    window.title('Lanis Management Tool')  # set window title for the application
    window.geometry('600x400')  # set fixed window size to 600x400 pixels
    window.resizable(False, False)  # disable window resizing horizontally and vertically
    window.configure(bg='#F3F3F3')  # set the background color of the window
    # Do not keep the window permanently on top

    show_password_var = tk.IntVar()  # create an IntVar to track the 'show password' checkbox state

    def get_userdata():  # nested function to read user input and start authentication
        school_id = school_id_entry.get()  # read the school ID from the input field
        name_lastname = name_lastname_entry.get()  # read the username from the input field
        password = password_entry.get()  # read the password from the input field

        # Input validation
        if not school_id.strip() or not name_lastname.strip() or not password:  # ensure no field is empty or only whitespace
            messagebox.showwarning('Warning', 'Please fill in all fields.')  # warn the user about missing fields
            return  # abort if validation fails

        # Start authentication in a background thread so the GUI doesn't block
        def auth_thread():  # worker function to call lanis_client in the background
            try:
                lanis_client(school_id, name_lastname, password)  # call the function that handles Lanis interaction
            except Exception as error:
                logging.exception('Error running lanis_client: %s', error)  # log any exception raised during background auth
                window.after(0, lambda: messagebox.showerror('Error', f'Login error: {error}'))  # schedule an error dialog on the GUI thread

        threading.Thread(target=auth_thread, daemon=True).start()  # start the background thread as a daemon so it won't block exit

    def show_connection_window():  # nested function to present a small connection check dialog
        connection_window = tk.Toplevel(window)  # create a new top-level window attached to the main window
        connection_window.title('Check Connection & User Information')  # set its title
        connection_window.geometry('400x200')  # set its size
        connection_window.resizable(False, False)  # prevent resizing
        connection_window.configure(bg='#F3F3F3')  # set background color
        # connection_window.attributes('-topmost', True)
        connection_window.grab_set()  # grab focus so the user interacts with this dialog first

        tk.Label(connection_window, text="Check Internet Connection...", bg='#F3F3F3', font="Arial 10").pack(pady=5)  # label prompting internet check
        internet_status_label = tk.Label(connection_window, text='', bg='#F3F3F3', font='Arial 13')  # label used to show internet status
        internet_status_label.pack()  # add the status label to the layout

        tk.Label(connection_window, text="Check User information...", bg='#F3F3F3', font="Arial 10").pack(pady=5)  # label prompting user info check
        userinfo_status_label = tk.Label(connection_window, text='', bg='#F3F3F3', font='Arial 13')  # label used to show user info status
        userinfo_status_label.pack()  # add the user info label to the layout

        progress = ttk.Progressbar(connection_window, orient="horizontal", length=300, mode="indeterminate")  # create an indeterminate progress bar
        progress.pack(pady=10)  # add progress bar to layout with vertical padding
        progress.start(10)  # start the progress animation with a 10ms interval

        def check_internet_connection(host="8.8.8.8", port=53, timeout=3):  # function to check internet connectivity to a known host
            def update_message(success):  # inner helper to update GUI based on connectivity result
                if success:
                    internet_status_label.config(text="Internet connection successful")  # show success message
                    connection_window.after(800, check_user_information)  # schedule the user info check after a small delay
                else:
                    progress.stop()  # stop the progress animation
                    internet_status_label.config(text="No internet connection")  # show failure message
                    messagebox.showerror('Error', 'No internet connection available.')  # inform the user about lack of internet

            def perform_check():  # worker that performs a socket connection test
                try:
                    socket.setdefaulttimeout(timeout)  # set a default timeout for socket operations
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create a TCP socket
                    try:
                        s.connect((host, port))  # attempt to connect to the host and port
                        # Update GUI from main thread
                        connection_window.after(0, lambda: update_message(True))  # schedule success update on GUI thread
                    finally:
                        s.close()  # ensure the socket is closed
                except socket.error:
                    connection_window.after(0, lambda: update_message(False))  # schedule failure update on GUI thread if connection fails

            # Start the network check in its own thread so it doesn't block the GUI
            threading.Thread(target=perform_check, daemon=True).start()  # run the network check in a daemon thread

        def check_user_information():  # function to initiate user information checks (and start authentication)
            try:
                userinfo_status_label.config(text="Checking user information...")  # update status label for user info check
                # get_userdata starts authentication in a background thread
                get_userdata()  # call get_userdata which in turn starts background auth
                userinfo_status_label.config(text="User information check started")  # indicate the check has started
            except Exception as error:
                userinfo_status_label.config(text="Error during check")  # update label on error
                logging.exception('Error in check_user_information: %s', error)  # log exception details
                messagebox.showerror("Error", f"An error occurred: {error}")  # show error dialog to the user
            finally:
                progress.stop()  # stop the progress bar regardless of outcome

        check_internet_connection()  # start the internet check when showing the connection window

    def show_password_function():  # toggle function to show or hide the password field
        password_entry.configure(show="" if show_password_var.get() else "*")  # configure the password entry widget to show or mask text

    def quit_function():  # function to confirm and quit the application
        if messagebox.askquestion('Warning', 'Are you sure?', icon='warning') == 'yes':  # confirm with the user before quitting
            window.quit()  # close the main window and end the Tkinter loop

    window.protocol('WM_DELETE_WINDOW', quit_function)  # bind the window close button to the quit_function

    # Header
    tk.Label(window, text='Lanis Management Tool', bg='#F3F3F3', font='Arial 20 bold').pack(anchor='n', pady=20)  # add a header label at the top of the window

    # School ID
    tk.Label(window, text='School ID (1234):', font="Arial 9", bg='#F3F3F3').place(x=177, y=80)  # label for the school ID input
    school_id_entry = tk.Entry(window, width=40)  # create an entry widget for school ID input
    school_id_entry.place(x=180, y=110)  # position the school ID entry widget

    # Username
    tk.Label(window, text='name.lastname (max.mustermann):', font="Arial 9", bg='#F3F3F3').place(x=177, y=140)  # label for username input
    name_lastname_entry = tk.Entry(window, width=40)  # create an entry widget for username input
    name_lastname_entry.place(x=180, y=170)  # position the username entry widget

    # Password
    tk.Label(window, text='Password:', font="Arial 9", bg='#F3F3F3').place(x=177, y=200)  # label for password input
    password_entry = tk.Entry(window, show='*', width=40)  # create a password entry widget that masks input
    password_entry.place(x=180, y=230)  # position the password entry widget

    # Show password checkbox
    tk.Checkbutton(window, text='Show Password', variable=show_password_var, command=show_password_function, bg='#F3F3F3').place(x=180, y=260)  # checkbox to toggle password visibility

    # Buttons
    login_button = tk.Button(window, text='Login', font="Arial 10 bold", cursor="hand2",bg="blue", fg="white", width=8, command=show_connection_window)  # create the Login button that opens the connection check dialog
    login_button.place(x=180, y=290)  # position the Login button

    tk.Button(window, text='Quit', font="Arial 10 bold", cursor="hand2",bg="red", fg="white", width=8, command=quit_function).place(x=350, y=290)  # create and position a Quit button that triggers quit_function

    window.mainloop()  # enter the Tkinter main loop to start the GUI event handling


userinterface_window()  # call the function to build and show the GUI when the script runs
