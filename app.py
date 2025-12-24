import tkinter as tk
from tkinter import messagebox, ttk
import socket
import threading
import logging
from lanisapi import LanisClient, LanisAccount
from lanisapi.exceptions import LoginPageRedirectError

# Configure logging to a file with timestamps for diagnostics
logging.basicConfig(
    filename='html_logs.txt',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)


class LanisApp:
    """
    Main application class that builds the GUI and handles interactions.

    All background operations (network checks, authentication) run in daemon
    threads to keep the GUI responsive. Any GUI updates from background threads
    are scheduled onto the main thread using self.root.after(...).
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Lanis Management Tool")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        self.root.configure(bg="#F3F3F3")

        # Variable to control password visibility checkbox
        self.show_password_var = tk.IntVar(value=0)

        # Build user interface
        self._build_ui()

        # Holders for the temporary "connection" window and progressbar
        self.connection_window = None
        self.progress = None

    def _build_ui(self):
        """Create and place all widgets on the main window."""
        # Header label
        tk.Label(self.root, text="Lanis Management Tool", bg="#F3F3F3", font="Arial 20 bold").pack(anchor='n', pady=20)

        # School ID label and entry
        tk.Label(self.root, text="School ID (1234):", font="Arial 9", bg="#F3F3F3").place(x=177, y=80)
        self.school_id_entry = tk.Entry(self.root, width=40)
        self.school_id_entry.place(x=180, y=110)

        # Username label and entry
        tk.Label(self.root, text="name.lastname (max.mustermann):", font="Arial 9", bg="#F3F3F3").place(x=177, y=140)
        self.name_lastname_entry = tk.Entry(self.root, width=40)
        self.name_lastname_entry.place(x=180, y=170)

        # Password label and entry (masked)
        tk.Label(self.root, text="Password:", font="Arial 9", bg="#F3F3F3").place(x=177, y=200)
        self.password_entry = tk.Entry(self.root, show="*", width=40)
        self.password_entry.place(x=180, y=230)

        # Checkbox to toggle password visibility
        tk.Checkbutton(
            self.root,
            text="Show Password",
            variable=self.show_password_var,
            command=self._toggle_password,
            bg="#F3F3F3"
        ).place(x=180, y=260)

        # Login button (opens the connection check window)
        self.login_button = tk.Button(
            self.root, text="Login", font="Arial 10 bold", cursor="hand2",
            bg="blue", fg="white", width=8, command=self._show_connection_window
        )
        self.login_button.place(x=180, y=290)

        # Quit button to close the application
        self.quit_button = tk.Button(
            self.root, text="Quit", font="Arial 10 bold", cursor="hand2",
            bg="red", fg="white", width=8, command=self._quit
        )
        self.quit_button.place(x=350, y=290)

        # Ensure our quit handler runs when the window is closed via the window manager
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _toggle_password(self):
        """Show or hide the password based on the checkbox value."""
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def _quit(self):
        """Ask the user for confirmation and close the application."""
        if messagebox.askyesno("Warning", "Are you sure you want to quit?"):
            self.root.destroy()

    def _show_connection_window(self):
        """Create a modal-like small window that displays connection checks and progress."""
        # If the connection window already exists, don't open another
        if self.connection_window and tk.Toplevel.winfo_exists(self.connection_window):
            return

        # Create the Toplevel window for connection checks
        self.connection_window = tk.Toplevel(self.root)
        self.connection_window.title("Check Connection & User Information")
        self.connection_window.geometry("420x220")
        self.connection_window.resizable(False, False)
        self.connection_window.configure(bg="#F3F3F3")
        self.connection_window.transient(self.root)
        self.connection_window.grab_set()  # make it modal-like

        # Labels to show internet and user info status
        tk.Label(self.connection_window, text="Check Internet Connection...", bg="#F3F3F3", font="Arial 10").pack(pady=(10, 0))
        self.internet_status_label = tk.Label(self.connection_window, text="", bg="#F3F3F3", font="Arial 12")
        self.internet_status_label.pack()

        tk.Label(self.connection_window, text="Check user information...", bg="#F3F3F3", font="Arial 10").pack(pady=(10, 0))
        self.userinfo_status_label = tk.Label(self.connection_window, text="", bg="#F3F3F3", font="Arial 12")
        self.userinfo_status_label.pack()

        # Indeterminate progress bar to indicate activity
        self.progress = ttk.Progressbar(self.connection_window, orient="horizontal", length=350, mode="indeterminate")
        self.progress.pack(pady=12)
        self.progress.start(10)

        # Disable main window interaction while checks run
        self._set_interaction_enabled(False)

        # Run the internet connectivity check in a background daemon thread
        threading.Thread(target=self._check_internet_connection, daemon=True).start()

    def _set_interaction_enabled(self, enabled: bool):
        """
        Enable or disable main window interactive widgets.

        Disabling prevents the user from starting another check while one runs.
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.login_button.configure(state=state)
        self.quit_button.configure(state=state)
        # Optionally disable entries too so the user cannot edit while checks run
        self.school_id_entry.configure(state=state)
        self.name_lastname_entry.configure(state=state)
        self.password_entry.configure(state=state)

    def _check_internet_connection(self, host="8.8.8.8", port=53, timeout=3):
        """
        Attempt a TCP connection to a well-known host to verify internet connectivity.
        All GUI updates are scheduled on the main thread using self.root.after.
        """
        try:
            # socket.create_connection handles address resolution and connect with timeout
            with socket.create_connection((host, port), timeout=timeout):
                logging.info("Internet connection successful")
                self.root.after(0, lambda: self._on_internet_check_result(True))
                return
        except OSError as e:
            logging.warning("Internet connection failed: %s", e)
            self.root.after(0, lambda: self._on_internet_check_result(False))

    def _on_internet_check_result(self, success: bool):
        """Handle the result of the internet connectivity check on the main thread."""
        # If the connection window was closed meanwhile, re-enable main UI and exit
        if not self.connection_window or not tk.Toplevel.winfo_exists(self.connection_window):
            self._set_interaction_enabled(True)
            return

        if success:
            self.internet_status_label.config(text="Internet connection successful")
            # Proceed to user authentication; show a small delay to let the user read the status
            self.userinfo_status_label.config(text="Starting authentication...")
            self.connection_window.after(500, self._start_authentication)
        else:
            # Stop the progress indicator and inform the user about missing internet
            self.progress.stop()
            self.internet_status_label.config(text="No internet connection")
            messagebox.showerror("Error", "No internet connection available.")
            self._cleanup_after_connection_check()

    def _start_authentication(self):
        """Validate inputs and start the authentication process in a background thread."""
        school_id = self.school_id_entry.get().strip()
        name_lastname = self.name_lastname_entry.get().strip()
        password = self.password_entry.get()

        # Basic input validation
        if not school_id or not name_lastname or not password:
            self.progress.stop()
            messagebox.showwarning("Warning", "Please fill in all fields.")
            self._cleanup_after_connection_check()
            return

        # Update UI and start authentication
        self.userinfo_status_label.config(text="Authenticating...")
        self._set_interaction_enabled(False)

        threading.Thread(
            target=self._auth_worker,
            args=(school_id, name_lastname, password),
            daemon=True
        ).start()

    def _auth_worker(self, school_id, name_lastname, password):
        """
        Perform authentication and fetch tasks using the Lanis API.

        Any GUI interaction is scheduled to run on the main thread via self.root.after.
        A single re-authentication attempt is made if a LoginPageRedirectError occurs.
        """
        client = None
        try:
            logging.info("Authenticating user %s@%s", name_lastname, school_id)
            client = LanisClient(LanisAccount(school_id, name_lastname, password))
            client.authenticate()

            try:
                tasks = client.get_tasks()
            except LoginPageRedirectError as e:
                # The API may have redirected to the login page (session expired).
                logging.warning("Session may be expired (login page returned): %s", e)
                # Attempt a single re-authentication and retry
                try:
                    logging.info("Attempting re-authentication for user %s@%s", name_lastname, school_id)
                    client.authenticate()
                    tasks = client.get_tasks()
                except LoginPageRedirectError as e2:
                    logging.exception("Re-authentication failed: %s", e2)
                    # Report the error back to the main thread
                    self.root.after(0, lambda: self._on_auth_result(error=e2))
                    return

            # If we get here, tasks was retrieved (or something else returned)
            self.root.after(0, lambda: self._on_auth_result(tasks=tasks))

        except Exception as e:
            logging.exception("Error in Lanis client: %s", e)
            # Send the exception to the main thread handler
            self.root.after(0, lambda: self._on_auth_result(error=e))
        finally:
            # Ensure the client is closed to release any resources
            try:
                if client:
                    client.close()
            except Exception as e3:
                # Ignore close errors; they shouldn't mask the original exception
                pass

    def _on_auth_result(self, tasks=None, error=None):
        """Handle the authentication result on the main thread and update UI accordingly."""
        # Stop the progress indicator
        if self.progress:
            self.progress.stop()

        if error:
            # Distinguish between session redirect and generic errors
            if isinstance(error, LoginPageRedirectError):
                messagebox.showerror(
                    "Session Error",
                    "Lanis returned the login page. Your session may have expired — please try logging in again."
                )
            else:
                messagebox.showerror("Error", f"An error occurred while connecting: {error}")
            self.userinfo_status_label.config(text="Authentication failed")
            logging.info("Authentication failed: %s", error)
            self._cleanup_after_connection_check()
            return

        # Success path: tasks may be a list or something else depending on the API
        if isinstance(tasks, list) and tasks:
            message = f"Found {len(tasks)} tasks."
            logging.info(message)
            messagebox.showinfo("Tasks", message)
            self.userinfo_status_label.config(text="Tasks retrieved")
        else:
            logging.info("No tasks returned or unknown format")
            messagebox.showinfo("Tasks", "No tasks found or unknown format.")
            self.userinfo_status_label.config(text="No tasks found")

        # Optionally clear entries on successful login:
        # self._clear_entries()
        self._cleanup_after_connection_check()

    def _cleanup_after_connection_check(self):
        """
        Re-enable main UI controls and destroy the connection window if present.
        This should always run on the main thread.
        """
        try:
            if self.connection_window and tk.Toplevel.winfo_exists(self.connection_window):
                self.connection_window.grab_release()
                self.connection_window.destroy()
        except Exception:
            logging.exception("Error while cleaning up connection window")
        finally:
            self.connection_window = None
            self.progress = None
            self._set_interaction_enabled(True)

    def _clear_entries(self):
        """Clear the contents of the input entry widgets."""
        try:
            self.school_id_entry.delete(0, tk.END)
            self.name_lastname_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
        except Exception:
            logging.exception("Error when clearing entries")


def main():
    """Create the main Tk instance and run the application."""
    root = tk.Tk()
    app = LanisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
