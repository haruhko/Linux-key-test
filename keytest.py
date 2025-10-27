#!/usr/bin/env python3

import tkinter as tk
from datetime import datetime
from tkinter import ttk, scrolledtext
import tkinter.messagebox # Necesario para el botón de Reset
import threading
import time

#Importar pynput para captura de eventos y suprecion del sistema
try:
    from pynput import keyboard
except ImportError:
    print("ERROR:  'pynput' not installed. It is no possible supress some keys on the system.")
    
    # Crea un mock para evitar errores graves si pynput no está instalado
    class MockKeyboard:
        Key = type('Key', (object,), {'esc': 'Escape', 'cmd': 'Super_L', 'print_screen': 'Print'})
        def Listener(self, *args, **kwargs): return self
        def start(self): pass
        def join(self): pass
    keyboard = MockKeyboard()


class KeyboardTester:
    """Aplicación para testear las pulsaciones de teclas y su latencia con soporte para QWERTY y AZERTY,
    incluyendo mapeo de mayúsculas/minúsculas y botón de reset."""
    
    def __init__(self, master):
        self.master = master
        master.title("Keyboard Tester (US / FRENCH)")
        master.geometry("1100x750") # Tamaño ajustado para un mejor diseño
        
        # --- Variables de estado ---
        self.key_press_times = {}
        self.pressed_keys = set()  # Almacena las teclas que ya fueron presionadas
        self.default_color = "gray80"
        self.active_color = "green"
        self.tested_color = "khaki1"  # Color amarillo suave para teclas ya testeadas

        # --- Configuración de Pynput (Mapeo de teclas especiales) ---
        # Mapea las teclas de pynput a los keysyms de Tkinter
        self.key_map = {

            keyboard.Key.cmd_l: 'Super_L', # Tecla Windows/Super
            keyboard.Key.cmd_r: 'Super_R', # Tecla Windows/Super
            keyboard.Key.print_screen: 'Print' # Tecla Print Screen
            # ... otros mapeos especiales según necesites ...
        }
        # --- Definición de Layouts ---
        self.layouts = {
            "English (QWERTY)": self._get_qwerty_layout(),
            "French (AZERTY)": self._get_azerty_layout(),
        }

        # --- Layout de la Interfaz ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 1. Controles, Selector de Distribución y Botón de Reset
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)

        ttk.Label(control_frame, text="Select Distribución:").pack(side="left", padx=5)
        
        self.layout_selector = ttk.Combobox(
            control_frame, 
            values=list(self.layouts.keys()), 
            state="readonly",
            width=20
        )
        self.layout_selector.current(0) # Seleccionar QWERTY por defecto
        self.layout_selector.bind("<<ComboboxSelected>>", self.switch_layout)
        self.layout_selector.pack(side="left", padx=5)
        
        # Botón de Reset
        ttk.Button(control_frame, text="🔁 Reset Keys", command=self.reset_tested_keys).pack(side="right")


        # 2. Contenedor Principal (Teclado + Lista)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        # 2.1. Zona del Teclado (Izquierda)
        self.keyboard_frame = ttk.LabelFrame(content_frame, text="Keyboard", padding="10")
        self.keyboard_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # 2.2. Zona de Latencias (Derecha) con Scrollbar
        latency_group = ttk.LabelFrame(content_frame, text="Key Latency (ms)", padding="10")
        latency_group.pack(side="right", fill="y", padx=10)
        
        # Lista para mostrar las latencias
        list_frame = ttk.Frame(latency_group)
        list_frame.pack(fill="both", expand=True)
        
        self.latency_listbox = tk.Listbox(list_frame, width=35, height=25, font=("Courier", 10))
        self.latency_listbox.pack(side="left", fill="both", expand=True)

        # Scrollbar para la lista de latencias
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.latency_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.latency_listbox.config(yscrollcommand=scrollbar.set)
        # ¡IMPORTANTE! Desactivar los bindings de Tkinter, ya que pynput toma el control total.
        # master.bind('<KeyPress>', self.on_key_press)
        # master.bind('<KeyRelease>', self.on_key_release)

        # --- Información del Autor ---
        self.author_label = tk.Label(master, 
                                     text="By Andres V. a.k.a. 4vs3c", 
                                     font=("Arial", 8), 
                                     fg="gray50") # Color de texto gris suave
        self.author_label.pack(side="bottom", pady=5) # Abajo de todo, con un pequeño padding
        
        # --- Inicialización y Eventos ---
        self.key_widgets = {} 
        self.current_layout_name = self.layout_selector.get()
        self._draw_keyboard(self.layouts[self.current_layout_name])

        master.bind('<KeyPress>', self.on_key_press)
        master.bind('<KeyRelease>', self.on_key_release)
        master.bind('<FocusIn>', lambda e: master.focus_set()) # Asegurar que la ventana tiene el foco

    # 3. Iniciar el Listener de pynput y el Polling de la Cola
        self._start_keyboard_listener()
        self.master.after(10, self.process_tk_queue) 
        
        # Manejo de cierre para detener el Listener
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------------------------------------------------------------
    # --- Lógica de pynput y Threading ---
    # ---------------------------------------------------------------------

    def _get_keysym(self, key):
        """Traduce un objeto de tecla de pynput a un keysym de Tkinter."""
        if isinstance(key, keyboard.KeyCode):
            # Para teclas alfanuméricas/símbolos, usa el carácter o su mayúscula
            return key.char if key.char is not None else str(key)
        elif isinstance(key, keyboard.Key):
            # Para teclas especiales, usa el mapeo
            return self.key_map.get(key, str(key)).replace('_L', '').replace('_R', '')
        return str(key)
        
    def on_press_pynput(self, key):
        """Maneja el evento KeyPress desde el hilo de pynput."""
        keysym = self._get_keysym(key)
        # Enviar el evento al hilo principal de Tkinter
        self.tk_queue.append(('key_press', keysym))
        
    def on_release_pynput(self, key):
        """Maneja el evento KeyRelease desde el hilo de pynput."""
        keysym = self._get_keysym(key)
        # Enviar el evento al hilo principal de Tkinter
        self.tk_queue.append(('key_release', keysym))

    def _start_keyboard_listener(self):
        """Inicia el listener de pynput en un hilo separado con supresión."""
        # suppress=True es la clave para bloquear las funciones del sistema (Super, PrtSc)
        self.listener = keyboard.Listener(
            on_press=self.on_press_pynput,
            on_release=self.on_release_pynput,
            suppress=True  
        )
        self.listener.start()

    def process_tk_queue(self):
        """Procesa los eventos de la cola en el hilo principal de Tkinter."""
        while self.tk_queue:
            event_type, keysym = self.tk_queue.pop(0)
            
            if event_type == 'key_press':
                self._handle_key_press_ui(keysym)
            elif event_type == 'key_release':
                self._handle_key_release_ui(keysym)
                
        # Continuar el polling (10ms)
        self.master.after(10, self.process_tk_queue) 
        
    def _handle_key_press_ui(self, keysym):
        """Lógica de Tkinter para la pulsación de tecla."""
        self.key_press_times[keysym] = datetime.now()
        # Asegúrate de que las mayúsculas/minúsculas también pinten el widget
        if keysym in self.key_widgets:
            self.key_widgets[keysym].config(bg=self.active_color)
        elif keysym.lower() in self.key_widgets:
             self.key_widgets[keysym.lower()].config(bg=self.active_color)

    def _handle_key_release_ui(self, keysym):
        """Lógica de Tkinter para la liberación de tecla y cálculo de latencia."""
        
        # Identificar el keysym correcto para el widget
        target_keysym = keysym
        if target_keysym not in self.key_widgets and target_keysym.lower() in self.key_widgets:
            target_keysym = target_keysym.lower()
        
        # 1. Calcular Latencia
        latency_ms = None
        if target_keysym in self.key_press_times:
            press_time = self.key_press_times.pop(target_keysym)
            release_time = datetime.now()
            latency_ms = (release_time - press_time).total_seconds() * 1000
            latency_text = f"[{target_keysym:^15}]: {latency_ms:7.2f} ms"
            self.latency_listbox.insert(0, latency_text) 
            
        # 2. Marcar como testeada
        if target_keysym in self.key_widgets:
            self.pressed_keys.add(target_keysym) 
            self.key_widgets[target_keysym].config(bg=self.tested_color)
            
    def on_closing(self):
        """Detiene el listener de pynput antes de cerrar la ventana."""
        if self.listener.is_alive():
            self.listener.stop()
        self.master.destroy()

    # ---------------------------------------------------------------------
    # --- Definiciones de Layouts (Ajustados con la tecla 'Super') ---
    # ---------------------------------------------------------------------

    def _get_common_special_keys(self):
        """Define las teclas de función y navegación comunes a ambos layouts."""
        return [
           
            
            # Separador para teclado principal
            [] 
        ]
    
    def _get_qwerty_layout(self):
        """Layout QWERTY estándar (US/UK) con keysyms minúsculos para letras."""
        layout = self._get_common_special_keys() + [
              # Fila de Funciones y Escape
            [("Escape", "Esc", 1.5), ("F1", "F1"), ("F2", "F2"), ("F3", "F3"), ("F4", "F4"), 
             ("F5", "F5"), ("F6", "F6"), ("F7", "F7"), ("F8", "F8"), 
             ("F9", "F9"), ("F10", "F10"), ("F11", "F11"), ("F12", "F12"),
             ("Num_Lock", "NumLk"),("Print", "PrtSc"), ("Scroll_Lock", "ScrLk"), ("Pause", "Pause")],
            # Fila 1 (Números y Backspace)
            [("grave", "~ `"), ("1", "1 !"), ("2", "2 @"), ("3", "3 #"), ("4", "4 $"), 
             ("5", "5 %"), ("6", "6 ^"), ("7", "7 &"), ("8", "8 *"), ("9", "9 ("), 
             ("0", "0 )"), ("minus", "- _"), ("equal", "= +"), ("BackSpace", "⌫ Bksp", 2.2), ("Home", "Home"),("End", "End")],
            # Fila 2 (QWERTY)
            [("Tab", "↹ Tab", 1.7), ("q", "Q"), ("w", "W"), ("e", "E"), ("r", "R"), 
             ("t", "T"), ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), 
             ("p", "P"), ("bracketleft", "[ {"), ("bracketright", "] }"), ("backslash", "\\ |", 1.3), ("Prior", "PgUp")],
            # Fila 3 (ASDF)
            [("Caps_Lock", "⇪ Caps", 2.0), ("a", "A"), ("s", "S"), ("d", "D"), ("f", "F"), 
             ("g", "G"), ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), 
             ("semicolon", "; :"), ("apostrophe", "' \""), ("Return", "⏎ Enter", 2.0),  ("Next", "PgDn")],
            # Fila 4 (Shift)
            [("Shift_L", "⇧ Shift", 2.5), ("z", "Z"), ("x", "X"), ("c", "C"), 
             ("v", "V"), ("b", "B"), ("n", "N"), ("m", "M"), ("comma", ", <"), 
             ("period", ". >"), ("slash", "/ ?"), ("Shift_R", "⇧ Shift", 3.0), ("","",0.25),("Up", "↑"),],
            # Fila 5 (Control, Super, Alt, Space) - Super es 'Super_L' en Tkinter
            [("Control_L", "Ctrl", 1.3), ("Super_L", "❖ Super", 1.7), ("Alt_L", "Alt", 1.3), 
             ("space", "Espacio", 7.0), 
             ("Alt_R", "Alt", 1.3), ("Menu", "Menu", 1.3),("Insert", "Ins"),("Delete", "Del"), ("Left", "←"), ("Down", "↓"), ("Right", "→")],
        ]
        return layout

    def _get_azerty_layout(self):
        """Layout AZERTY estándar (Francés) con keysyms minúsculos para letras."""
        layout = self._get_common_special_keys() + [
            # Fila 1 (Números y Backspace)
            [("twosuperior", "²"), ("ampersand", "1 &"), ("eacute", "2 é"), ("quotedbl", "3 \""), ("apostrophe", "4 '"), 
             ("parenleft", "5 ("), ("section", "6 -"), ("egrave", "7 è"), ("underscore", "8 _"), ("ccedilla", "9 ç"), 
             ("agrave", "0 à"), ("parenright", ")"), ("equal", "= +"), ("BackSpace", "⌫ Bksp", 2.2)],
            # Fila 2 (AZERTY)
            [("Tab", "↹ Tab", 1.7), ("a", "A"), ("z", "Z"), ("e", "E"), ("r", "R"), 
             ("t", "T"), ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), 
             ("p", "P"), ("dead_circumflex", "^ ¨"), ("dollar", "$ £"), ("asterisk", "* µ", 1.3)],
            # Fila 3 (QSDF)
            [("Caps_Lock", "⇪ Caps", 2.0), ("q", "Q"), ("s", "S"), ("d", "D"), ("f", "F"), 
             ("g", "G"), ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), 
             ("m", "M"), ("ugrave", "ù %"), ("Return", "⏎ Enter", 2.6)],
            # Fila 4 (Shift)
            [("Shift_L", "⇧ Shift", 2.5), ("less", "< >"), ("w", "W"), ("x", "X"), ("c", "C"), 
             ("v", "V"), ("b", "B"), ("n", "N"), ("comma", ","), ("semicolon", ";"), 
             ("colon", ": /"), ("Shift_R", "⇧ Shift", 3.0)],
            # Fila 5 (Control, Super, Alt, Space)
            [("Control_L", "Ctrl", 1.3), ("Super_L", "❖ Super", 1.3), ("Alt_L", "Alt", 1.3), 
             ("space", "Espacio", 7.0), 
             ("Alt_R", "Alt", 1.3), ("Super_R", "❖ Super", 1.3), ("Control_R", "Ctrl", 1.3)],
        ]
        return layout

    # ---------------------------------------------------------------------
    # --- Funciones de Interfaz (Modificado el mapeo) ---
    # ---------------------------------------------------------------------

    def _clear_keyboard_frame(self):
        """Elimina todos los widgets del marco del teclado."""
        for widget in self.keyboard_frame.winfo_children():
            widget.destroy()
        self.key_widgets = {}

    def switch_layout(self, event):
        """Cambia el layout del teclado cuando se selecciona una nueva opción."""
        new_layout_name = self.layout_selector.get()
        if new_layout_name != self.current_layout_name:
            self.current_layout_name = new_layout_name
            self._clear_keyboard_frame()
            self._draw_keyboard(self.layouts[new_layout_name])
            
            # Restaurar colores de teclas previamente presionadas
            for keysym in self.pressed_keys:
                 if keysym in self.key_widgets:
                    self.key_widgets[keysym].config(bg=self.tested_color)
            
    def reset_tested_keys(self):
        """Reinicia el estado de las teclas testeadas (color amarillo) y la lista de latencias."""
        if not tkinter.messagebox.askyesno("Confirm Reset", "¿Are you sure you want to reset all keys?"):
            return

        self.pressed_keys.clear()
        self.key_press_times.clear()
        self.latency_listbox.delete(0, tk.END)
        
        # Devolver el color de todas las teclas al estado por defecto
        for widget in self.key_widgets.values():
            widget.config(bg=self.default_color)
        
        #tkinter.messagebox.showinfo("Reset Completo", "El estado de las teclas y el historial de latencias han sido reseteados.")

    def _create_key_widget(self, parent, text, keysym, width_ratio=1):
        """
        Crea un Label para la tecla y la mapea a sí misma y a su versión mayúscula 
        (si es una letra) en self.key_widgets.
        """
        width = int(5 * width_ratio) 
        
        # Determinar el color inicial
        initial_color = self.tested_color if keysym in self.pressed_keys else self.default_color

        key_label = tk.Label(parent, 
                             text=text, 
                             bg=initial_color, 
                             relief="raised", 
                             borderwidth=2,
                             width=width,
                             height=2,
                             font=("Arial", 10, "bold"))
        
        # 1. Almacenar el keysym principal (ej: 'a')
        self.key_widgets[keysym] = key_label
        
        # 2. Si es una letra, mapear también la versión mayúscula (ej: 'A')
        # Esto soluciona el problema de que 's' y 'S' se manejen por separado.
        if len(keysym) == 1 and keysym.isalpha():
            self.key_widgets[keysym.upper()] = key_label
            
        return key_label

    def _draw_keyboard(self, layout):
        """Dibuja el layout del teclado en el marco."""
        for r_index, row in enumerate(layout):
            row_frame = ttk.Frame(self.keyboard_frame)
            row_frame.pack(fill="x", pady=2)
            
            for key_info in row:
                if not key_info[0]: # Ignorar los espacios vacíos
                    ttk.Label(row_frame, width=int(5 * key_info[2])).pack(side="left", padx=1)
                    continue

                keysym = key_info[0]
                text = key_info[1]
                width_ratio = key_info[2] if len(key_info) == 3 else 1
                
                key_widget = self._create_key_widget(row_frame, text, keysym, width_ratio)
                key_widget.pack(side="left", padx=1)

    # ---------------------------------------------------------------------
    # --- Manejo de Eventos de Teclado (Usa el mapeo mayús/minús) ---
    # ---------------------------------------------------------------------

    def on_key_press(self, event):
        """Maneja el evento de pulsación: pinta la tecla y registra el tiempo."""
        keysym = event.keysym
        
        # Registrar tiempo de pulsación
        self.key_press_times[keysym] = datetime.now()

        # Pintar la tecla activa (funcionará para 's' o 'S')
        if keysym in self.key_widgets:
            self.key_widgets[keysym].config(bg=self.active_color)
        
        # Nota: Como este es el script base de Tkinter, las teclas como Print Screen 
        # y Super seguirán activando la funcionalidad del sistema operativo, 
        # ya que Tkinter no puede bloquearlas. Solo el script con pynput puede hacer eso.

    def on_key_release(self, event):
        """Maneja el evento de liberación: calcula latencia y actualiza el estado."""
        keysym = event.keysym
        
        # 1. Calcular Latencia
        latency_ms = None
        if keysym in self.key_press_times:
            press_time = self.key_press_times.pop(keysym)
            release_time = datetime.now()
            
            latency_ms = (release_time - press_time).total_seconds() * 1000
            
            # Añadir a la lista de latencias
            latency_text = f"[{keysym:^15}]: {latency_ms:7.2f} ms"
            self.latency_listbox.insert(0, latency_text) 
            
        # 2. Marcar como testeada (Amarillo suave) y restaurar color
        if keysym in self.key_widgets:
            self.pressed_keys.add(keysym) # Añadir a las teclas ya presionadas
            self.key_widgets[keysym].config(bg=self.tested_color)

# --- Ejecución del Programa ---
if __name__ == '__main__':
    root = tk.Tk()
    app = KeyboardTester(root)
    root.mainloop()
