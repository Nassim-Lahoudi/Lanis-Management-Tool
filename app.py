from tkinter import Tk, Label, Entry, Button, IntVar, Checkbutton, messagebox
from lanisapi import LanisClient, LanisAccount

def lanis_client(school_id, name_lastname, password):
    client = LanisClient(LanisAccount(school_id, name_lastname, password))

    try:
        client.authenticate()
        tasks = client.get_tasks()

        if isinstance(tasks, list) and tasks:
            messagebox.showinfo("Aufgaben", f"Es wurden {len(tasks)} Aufgaben gefunden.")
        else:
            messagebox.showinfo("Aufgaben", f"Keine Aufgaben gefunden oder Format unbekannt.")
    except Exception as error:
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {error}")
    finally:
        client.close()

def userinterface_window():
    window: Tk = Tk()
    window.title('Lanis Aufgabenabruf')
    window.geometry('400x400')
    window.resizable(False, False)
    window.configure(bg='#F3F3F3')
    window.attributes('-topmost', True)

    show_password_var = IntVar()

    def get_userdata():
        school_id = school_id_entry.get()
        name_lastname = name_lastname_entry.get()
        password = password_entry.get()

        lanis_client(school_id, name_lastname, password)

    def show_password_function():
        show_password_var_storage = show_password_var.get()
        if show_password_var_storage:
            password_entry.configure(show="")
        else:
            password_entry.configure(show="*")



    school_id_label = Label(window, text='school ID: ', font="Arial 10 bold")
    school_id_entry = Entry(window)

    school_id_label.grid(row=0, column=0)
    school_id_entry.grid(row=0, column=1)

    name_lastname_label = Label(window, text='name.lastname: ', font="Arial 10 bold")
    name_lastname_entry = Entry(window)

    name_lastname_label.grid(row=1, column=0)
    name_lastname_entry.grid(row=1, column=1)

    password_label = Label(window, text='password: ', font="Arial 10 bold")
    password_entry = Entry(window, show='*')

    password_label.grid(row=2, column=0)
    password_entry.grid(row=2, column=1)

    show_password_checkbox = Checkbutton(window, text='show password', variable=show_password_var, command=show_password_function)
    show_password_checkbox.grid(row=3, column=0, columnspan=2)

    login_button = Button(window, text='Login', font="Arial 10 bold",command=get_userdata)
    login_button.grid(row=3, column=1)

    window.mainloop()

userinterface_window()
