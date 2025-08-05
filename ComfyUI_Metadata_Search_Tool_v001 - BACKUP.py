import os
import subprocess
import platform
import re
import webbrowser
from tkinter import (
    filedialog, Tk, Label, Entry, Button, Listbox,
    Scrollbar, END, SINGLE, StringVar, messagebox, Menu, Canvas
)
from PIL import Image, ImageTk
from datetime import datetime

APP_VERSION = "1.0"

def log_error(context, exception):
    with open("error_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR in {context}\n")
        log_file.write(f"{str(exception)}\n")

def extract_metadata(png_path):
    try:
        img = Image.open(png_path)
        return img.info
    except Exception as e:
        log_error("extract_metadata", e)
        return {}

def search_images(folder_path, include_keywords, exclude_keywords):
    if include_keywords:
        included_escaped = [re.escape(w.strip()) for w in include_keywords if w.strip()]
        include_pattern = re.compile(r'\b(' + '|'.join(included_escaped) + r')\b', re.IGNORECASE)
    else:
        include_pattern = None

    exclude_patterns = [re.compile(rf'\b{re.escape(word.strip())}\b', re.IGNORECASE) for word in exclude_keywords if word.strip()]

    matches = []
    excluded_count = 0

    for root_dir, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(".png"):
                full_path = os.path.join(root_dir, filename)
                metadata = extract_metadata(full_path)
                metadata_str = " ".join(str(v) for v in metadata.values())

                if include_pattern and not include_pattern.search(metadata_str):
                    continue

                if any(pattern.search(metadata_str) for pattern in exclude_patterns):
                    excluded_count += 1
                    continue

                matches.append(full_path)

    return matches, excluded_count

def choose_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_path_var.set(folder)
        result_list.delete(0, END)
        preview_canvas.delete("all")
        results_count_var.set("")

def run_search(event=None):
    folder = folder_path_var.get()
    include_raw = keyword_entry.get().strip()
    exclude_raw = exclude_entry.get().strip()

    include_list = [w for w in re.split(r'[,\s]+', include_raw) if w]
    exclude_list = [w for w in re.split(r'[,\s]+', exclude_raw) if w]

    if not folder or not include_list:
        messagebox.showinfo("Input Error", "((aaahn!~)) So hasty! :3 You have to choose a folder and enter at least one include keyword, step bro.")
        return

    result_list.delete(0, END)
    preview_canvas.delete("all")
    global matched_files
    matched_files, excluded_count = search_images(folder, include_list, exclude_list)
    if matched_files:
        for f in matched_files:
            result_list.insert(END, os.path.basename(f))
        result_list.selection_set(0)
        result_list.activate(0)
        update_preview()
    else:
        result_list.insert(END, "No matches found.")

    results_count_var.set(f"Results found: {len(matched_files)} | Excluded: {excluded_count}")

def open_image_viewer():
    selection = result_list.curselection()
    if not selection or not matched_files:
        return
    selected_file = matched_files[selection[0]]
    try:
        if platform.system() == "Windows":
            os.startfile(selected_file)
        elif platform.system() == "Darwin":
            subprocess.call(["open", selected_file])
        else:
            subprocess.call(["xdg-open", selected_file])
    except Exception as e:
        log_error("open_image_viewer", e)
        messagebox.showerror("Error", f"Failed to open image:\n{e}")

def show_in_explorer():
    selection = result_list.curselection()
    if not selection or not matched_files:
        return
    selected_file = matched_files[selection[0]]
    try:
        if platform.system() == "Windows":
            subprocess.run(f'explorer /select,"{selected_file}"', shell=True, check=True)
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", selected_file])
        else:
            subprocess.run(["xdg-open", os.path.dirname(selected_file)])
    except Exception as e:
        log_error("show_in_explorer", e)
        messagebox.showerror("Error", f"Failed to open folder:\n{e}")

def open_file_location():
    selection = result_list.curselection()
    if not selection or not matched_files:
        return
    selected_file = matched_files[selection[0]]
    try:
        normalized_path = os.path.normpath(selected_file)
        if platform.system() == "Windows":
            result = subprocess.run(f'explorer /select,"{normalized_path}"', shell=True)
            if result.returncode != 0:
                log_error("open_file_location", f"Explorer returned code {result.returncode} but file was opened.")
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", normalized_path])
        else:
            subprocess.run(["xdg-open", os.path.dirname(normalized_path)])
    except Exception as e:
        log_error("open_file_location", e)
        messagebox.showerror("Error", f"Failed to open folder:\n{e}")

def copy_file_path():
    selection = result_list.curselection()
    if not selection or not matched_files:
        messagebox.showinfo("Copy Path", "No file selected.")
        return
    selected_file = matched_files[selection[0]]
    root.clipboard_clear()
    root.clipboard_append(selected_file)
    messagebox.showinfo("Copy Path", f"Copied to clipboard:\n{selected_file}")

def copy_metadata_to_clipboard():
    selection = result_list.curselection()
    if not selection or not matched_files:
        messagebox.showinfo("Copy Metadata", "No file selected.")
        return
    selected_file = matched_files[selection[0]]
    metadata = extract_metadata(selected_file)
    if metadata:
        text = "\n".join(f"{k}: {v}" for k, v in metadata.items())
        root.clipboard_clear()
        root.clipboard_append(text)
        messagebox.showinfo("Copy Metadata", "Metadata copied to clipboard.")
    else:
        messagebox.showinfo("Copy Metadata", "No metadata found for this image.")

def update_preview(event=None):
    selection = result_list.curselection()
    if not selection or not matched_files:
        preview_canvas.delete("all")
        return
    selected_file = matched_files[selection[0]]
    try:
        img = Image.open(selected_file)
        canvas_width = preview_canvas.winfo_width()
        canvas_height = preview_canvas.winfo_height()
        img.thumbnail((canvas_width, canvas_height))
        preview_img = ImageTk.PhotoImage(img)
        preview_canvas.image = preview_img
        preview_canvas.delete("all")
        preview_canvas.create_image(canvas_width//2, canvas_height//2, anchor="center", image=preview_img)
    except Exception as e:
        log_error("update_preview", e)

def show_context_menu(event):
    if result_list.curselection():
        menu = Menu(root, tearoff=0)
        menu.add_command(label="Open in Default Viewer", command=open_image_viewer)
        menu.add_command(label="Open Containing Folder (Highlight File)", command=show_in_explorer)
        menu.tk_popup(event.x_root, event.y_root)

def preview_context_menu(event):
    selection = result_list.curselection()
    if not selection or not matched_files:
        return
    menu = Menu(root, tearoff=0)
    menu.add_command(label="Copy Metadata to Clipboard", command=copy_metadata_to_clipboard)
    menu.add_command(label="Open Image in Default Viewer", command=open_image_viewer)
    menu.add_command(label="Open Containing Folder (Highlight File)", command=open_file_location)
    menu.tk_popup(event.x_root, event.y_root)

def on_arrow_key(event):
    if not matched_files:
        return "break"

    cur_selection = result_list.curselection()
    if not cur_selection:
        index = 0
    else:
        index = cur_selection[0]

    if event.keysym == "Up":
        new_index = max(0, index - 1)
    elif event.keysym == "Down":
        new_index = min(len(matched_files) - 1, index + 1)
    else:
        return

    result_list.selection_clear(0, END)
    result_list.selection_set(new_index)
    result_list.activate(new_index)
    result_list.see(new_index)
    update_preview()

    return "break"

def on_resize(event):
    update_preview()

def author_label_click(event):
    webbrowser.open("https://x.com/aecii_3d")

root = Tk()
root.title("ComfyUI Metadata Search")
root.geometry("1000x700")

folder_path_var = StringVar()
results_count_var = StringVar()

Button(root, text="Choose Your ComfyUI output folder", command=choose_folder).grid(row=0, column=0, padx=5)

Label(root, text="Keyword(s) (include, comma or space separated):").grid(row=1, column=0, sticky="w")
keyword_entry = Entry(root, width=30)
keyword_entry.grid(row=1, column=1, padx=5, pady=5)

Label(root, text="Exclude Keyword(s) (comma or space separated):").grid(row=2, column=0, sticky="w")
exclude_entry = Entry(root, width=30)
exclude_entry.grid(row=2, column=1, padx=5, pady=5)

keyword_entry.bind("<Return>", run_search)
exclude_entry.bind("<Return>", run_search)

Button(root, text="Search", command=run_search).grid(row=3, column=0, columnspan=2, pady=5)

results_count_label = Label(root, textvariable=results_count_var, anchor="w")
results_count_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=5)

result_list = Listbox(root, selectmode=SINGLE, width=50, height=18)
result_list.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
result_list.bind("<Double-1>", lambda e: open_image_viewer())
result_list.bind("<<ListboxSelect>>", update_preview)
result_list.bind("<Button-3>", show_context_menu)
result_list.bind("<Up>", on_arrow_key)
result_list.bind("<Down>", on_arrow_key)

scrollbar = Scrollbar(root)
scrollbar.grid(row=5, column=2, sticky="ns")
result_list.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=result_list.yview)

Button(root, text="Open File Location", command=open_file_location).grid(row=6, column=0, pady=5)
Button(root, text="Copy File Path", command=copy_file_path).grid(row=6, column=1, pady=5)

root.grid_columnconfigure(3, weight=1)
for i in range(7):
    root.grid_rowconfigure(i, weight=1)

preview_canvas = Canvas(root)
preview_canvas.grid(row=0, column=3, rowspan=8, padx=10, pady=10, sticky="nsew")
preview_canvas.bind("<Button-3>", preview_context_menu)

author_label = Label(root, text=f"Made by @aecii_3d (v{APP_VERSION})", fg="blue", cursor="hand2", font=("Segoe UI", 10, "underline"))
author_label.grid(row=0, column=3, sticky="ne", padx=10, pady=5)
author_label.bind("<Button-1>", author_label_click)

matched_files = []

root.bind("<Configure>", on_resize)

root.mainloop()
