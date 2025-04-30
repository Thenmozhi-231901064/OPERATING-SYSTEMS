import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# -------------------- Account Class ---------------------
class BankAccount:
    def __init__(self, name, balance, priority):
        self.name = name
        self.balance = balance
        self.priority = priority
        self.lock = threading.Lock()

    def withdraw(self, amount):
        self.balance -= amount

    def deposit(self, amount):
        self.balance += amount

# -------------------- Transfer Animation ---------------------
def animate_transfer(label):
    icons = [transfer_icon1, transfer_icon2, transfer_icon3]
    for _ in range(3):
        for icon in icons:
            label.config(image=icon)
            root.update_idletasks()
            time.sleep(0.3)
    label.config(image=success_icon)

def draw_arrow(canvas, nodes, from_acc, to_acc, amount):
    from_coords = nodes[from_acc.name]
    to_coords = nodes[to_acc.name]
    arrow = canvas.create_line(from_coords[0], from_coords[1], to_coords[0], to_coords[1],
                               arrow=tk.LAST, width=3, fill="blue")
    mid_x = (from_coords[0] + to_coords[0]) / 2
    mid_y = (from_coords[1] + to_coords[1]) / 2
    text = canvas.create_text(mid_x, mid_y - 10, text=f"${amount}", font=("Arial", 12), fill="blue")
    canvas.update()
    time.sleep(2)
    canvas.delete(arrow)
    canvas.delete(text)

# -------------------- Transaction Logic ---------------------
eff_data_deadlock = []
eff_data_nodl = []

def transfer_priority(from_acc, to_acc, amount, label, transactions_done, bar, anim_label,
                      canvas=None, nodes=None, eff_data=None, ax=None, canvas_fig=None):
    try:
        amount = float(amount)
        if amount <= 0:
            messagebox.showerror("Error", "Amount must be greater than zero!")
            return
    except ValueError:
        messagebox.showerror("Error", "Invalid amount!")
        return

    label.config(text=f"Attempting ${amount} transfer from {from_acc.name} to {to_acc.name}...")
    bar.start(10)
    threading.Thread(target=animate_transfer, args=(anim_label,)).start()

    start_time = time.time()

    if from_acc.priority == to_acc.priority:
        time.sleep(2)
        label.config(text=f"Deadlock! Same priority: {from_acc.name} & {to_acc.name}", foreground='red')
        anim_label.config(image=error_icon)
        bar.stop()
        transactions_done.append(False)
        check_final_status(transactions_done)
        return

    first, second = (from_acc, to_acc) if from_acc.priority < to_acc.priority else (to_acc, from_acc)

    with first.lock:
        label.config(text=f"{first.name} locked. Waiting for {second.name}...")
        time.sleep(1)
        if not second.lock.acquire(timeout=2):
            label.config(text=f"Deadlock detected! {from_acc.name} → {to_acc.name} failed.", foreground='red')
            bar.stop()
            anim_label.config(image=error_icon)
            transactions_done.append(False)
            check_final_status(transactions_done)
            return
        try:
            from_acc.withdraw(amount)
            to_acc.deposit(amount)
        finally:
            second.lock.release()

    end_time = time.time()
    duration = round(end_time - start_time, 2)

    label.config(text=f"  ${amount} transferred {from_acc.name} → {to_acc.name}", foreground='green')
    bar.stop()
    anim_label.config(image=success_icon)
    update_balance_labels()
    transactions_done.append(True)

    if canvas and nodes:
        draw_arrow(canvas, nodes, from_acc, to_acc, amount)

    if eff_data is not None and ax is not None and canvas_fig is not None:
        eff_data.append(duration)
        ax.clear()
        ax.set_facecolor("#f9f9f9")
        ax.set_title("Transaction Time Efficiency", fontsize=14, color='navy', pad=20)
        ax.set_xlabel("Transaction #", fontsize=12)
        ax.set_ylabel("Time (s)", fontsize=12)
        ax.tick_params(colors='black', labelsize=10)

        bars = ax.bar(range(1, len(eff_data) + 1), eff_data,
                      color=plt.cm.viridis([i / len(eff_data) for i in range(len(eff_data))]),
                      edgecolor="black")

        for bar, val in zip(bars, eff_data):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{val:.2f}s",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.grid(axis='y', linestyle='--', alpha=0.5)
        canvas_fig.draw()

    check_final_status(transactions_done)

def check_final_status(transactions_done):
    if len(transactions_done) == 4:
        if all(transactions_done):
            messagebox.showinfo("Result", "  All transactions completed successfully! No Deadlocks.")
        else:
            messagebox.showerror("Deadlock Result", f"  {transactions_done.count(False)} transaction(s) failed due to deadlock!")

# -------------------- UI Setup Functions ---------------------
def update_balance_labels():
    for i, acc in enumerate(bank_accounts):
        balance_labels[i].config(text=f"{acc.name} [Priority {acc.priority}] Balance: ${acc.balance}")

def build_transaction_ui(frame, account_pairs, transactions_done_list,
                         canvas=None, nodes=None, eff_data=None, ax=None, canvas_fig=None):
    global balance_labels
    balance_labels = []
    for acc in bank_accounts:
        l = ttk.Label(frame, text=f"{acc.name} [Priority {acc.priority}] Balance: ${acc.balance}", font=("Arial", 14))
        l.pack(pady=2)
        balance_labels.append(l)

    status_label = ttk.Label(frame, text="", font=("Arial", 13, "bold"))
    status_label.pack(pady=8)

    for from_acc, to_acc in account_pairs:
        trans_frame = ttk.Frame(frame)
        trans_frame.pack(pady=4)

        entry = ttk.Entry(trans_frame, width=10, font=("Arial", 12))
        entry.pack(side='left', padx=5)

        bar = ttk.Progressbar(trans_frame, orient='horizontal', length=100, mode='indeterminate')
        bar.pack(side='left', padx=5)

        anim = ttk.Label(trans_frame, image=default_icon)
        anim.pack(side='left', padx=5)

        btn = ttk.Button(trans_frame, text=f"{from_acc.name} → {to_acc.name}",
                         command=lambda f=from_acc, t=to_acc, e=entry, p=bar, a=anim:
                         threading.Thread(target=transfer_priority, args=(
                             f, t, e.get(), status_label, transactions_done_list, p, a,
                             canvas, nodes, eff_data, ax, canvas_fig)).start())
        btn.pack(side='left', padx=5)

# -------------------- Root Setup ---------------------
root = tk.Tk()
root.title("Account Transaction Visualizer")
root.geometry("1000x900")
root.configure(bg="#e6f2ff")

transfer_icon1 = ImageTk.PhotoImage(Image.open("transfer1.png").resize((50, 50)))
transfer_icon2 = ImageTk.PhotoImage(Image.open("transfer2.png").resize((50, 50)))
transfer_icon3 = ImageTk.PhotoImage(Image.open("transfer3.png").resize((50, 50)))
success_icon = ImageTk.PhotoImage(Image.open("success.png").resize((50, 50)))
error_icon = ImageTk.PhotoImage(Image.open("error.png").resize((50, 50)))
default_icon = ImageTk.PhotoImage(Image.open("bank.png").resize((50, 50)))

ttk.Label(root, text="  Account Transaction & Deadlock Visual Simulator", font=("Arial", 20, "bold"), foreground="darkblue").pack(pady=10)

notebook = ttk.Notebook(root)
notebook.pack(expand=1, fill="both", padx=10, pady=10)

# -------------------- Deadlock Tab ---------------------
deadlock_tab = ttk.Frame(notebook)
notebook.add(deadlock_tab, text="  Deadlock Demo")

canvas_deadlock = tk.Canvas(deadlock_tab, width=600, height=200, bg="white")
canvas_deadlock.pack(pady=10)

bank_accounts = [
    BankAccount("Account A", 5000, 1),
    BankAccount("Account B", 3000, 2),
    BankAccount("Account C", 4000, 2),
    BankAccount("Account D", 6000, 1)
]
node_coords_deadlock = {
    "Account A": (100, 100),
    "Account B": (250, 50),
    "Account C": (400, 100),
    "Account D": (250, 150)
}
for acc in bank_accounts:
    x, y = node_coords_deadlock[acc.name]
    canvas_deadlock.create_oval(x - 25, y - 25, x + 25, y + 25, fill="lightblue")
    canvas_deadlock.create_text(x, y, text=acc.name)

transactions_deadlock = [
    (bank_accounts[0], bank_accounts[1]),
    (bank_accounts[1], bank_accounts[2]),
    (bank_accounts[2], bank_accounts[3]),
    (bank_accounts[3], bank_accounts[0])
]
transactions_done_deadlock = []

fig_dl, ax_dl = plt.subplots(figsize=(6, 3))
canvas_fig_dl = FigureCanvasTkAgg(fig_dl, master=root)

build_transaction_ui(deadlock_tab, transactions_deadlock, transactions_done_deadlock,
                     canvas_deadlock, node_coords_deadlock,
                     eff_data_deadlock, ax_dl, canvas_fig_dl)

# -------------------- No Deadlock Tab ---------------------
no_deadlock_tab = ttk.Frame(notebook)
notebook.add(no_deadlock_tab, text="  No Deadlock Demo")

canvas_nodl = tk.Canvas(no_deadlock_tab, width=600, height=200, bg="white")
canvas_nodl.pack(pady=10)

bank_accounts = [
    BankAccount("Account A", 5000, 1),
    BankAccount("Account B", 3000, 2),
    BankAccount("Account C", 4000, 3),
    BankAccount("Account D", 6000, 4)
]
node_coords_nodl = {
    "Account A": (100, 100),
    "Account B": (250, 50),
    "Account C": (400, 100),
    "Account D": (250, 150)
}
for acc in bank_accounts:
    x, y = node_coords_nodl[acc.name]
    canvas_nodl.create_oval(x - 25, y - 25, x + 25, y + 25, fill="lightgreen")
    canvas_nodl.create_text(x, y, text=acc.name)

transactions_nodl = [
    (bank_accounts[0], bank_accounts[1]),
    (bank_accounts[1], bank_accounts[2]),
    (bank_accounts[2], bank_accounts[3]),
    (bank_accounts[3], bank_accounts[0])
]
transactions_done_nodl = []

fig_nodl, ax_nodl = plt.subplots(figsize=(6, 3))
canvas_fig_nodl = FigureCanvasTkAgg(fig_nodl, master=root)

build_transaction_ui(no_deadlock_tab, transactions_nodl, transactions_done_nodl,
                     canvas_nodl, node_coords_nodl,
                     eff_data_nodl, ax_nodl, canvas_fig_nodl)

# -------------------- Priority Tab ---------------------
priority_tab = ttk.Frame(notebook)
notebook.add(priority_tab, text="  Priority Info")

for acc in bank_accounts:
    ttk.Label(priority_tab, text=f"{acc.name} → Priority: {acc.priority}", font=("Arial", 14)).pack(pady=10)

# -------------------- Efficiency Graph Tab ---------------------
eff_tab = ttk.Frame(notebook)
notebook.add(eff_tab, text="  Efficiency Graph")

ttk.Label(eff_tab, text="  Deadlock Transactions", font=("Arial", 13, "bold")).pack(pady=(10, 0))
canvas_fig_dl.get_tk_widget().pack(in_=eff_tab, padx=10, pady=5)

ttk.Label(eff_tab, text="  No Deadlock Transactions", font=("Arial", 13, "bold")).pack(pady=(10, 0))
canvas_fig_nodl.get_tk_widget().pack(in_=eff_tab, padx=10, pady=5)

root.mainloop()
 	ReplyForward
