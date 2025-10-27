#!/usr/bin/env python3
import tkinter as tk
from datetime import datetime
from tkinter import ttk, scrolledtext

class KeyboardTester:
    """Aplicación para testear las pulsaciones de teclas y su latencia con soporte para QWERTY y AZERTY."""
    def __init__(self, master):
        self.master = master
        master.title("Testeador Visual de Teclado (QWERTY / AZERTY)")
        master.geometry("1000x700")
        
        # --- Variables de estado ---
        self.key_press_times = {}
        self.pressed_keys = set()  # Almacena las teclas que ya fueron presionadas
        self.default_color = "gray80"
        self.active_color = "green"
        self.tested_color = "khaki1"  # Color amarillo suave para teclas ya testeadas

        # --- Definición de Layouts ---
        self.layouts = {
            "Inglés (QWERTY)": self._get_qwerty_layout(),
            "Francés (AZERTY)": self._get_azerty_layout(),
        }

        # --- Layout de la Interfaz ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 1. Selector de Distribución
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)

        ttk.Label(control_frame, text="Selecciona Distribución:").pack(side="left", padx=5)
        
        self.layout_selector = ttk.Combobox(
            control_frame, 
            values=list(self.layouts.keys()), 
            state="readonly",
            width=20
        )
        self.layout_selector.current(0) # Seleccionar QWERTY por defecto
        self.layout_selector.bind("<<ComboboxSelected>>", self.switch_layout)
        self.layout_selector.pack(side="left", padx=5)

        # 2. Contenedor Principal (Teclado + Lista)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        # 2.1. Zona del Teclado (Izquierda)
        self.keyboard_frame = ttk.LabelFrame(content_frame, text="Teclado Visual", padding="10")
        self.keyboard_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # 2.2. Zona de Latencias (Derecha) con Scrollbar
        latency_group = ttk.LabelFrame(content_frame, text="Latencias Registradas (ms)", padding="10")
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
        
        # --- Inicialización y Eventos ---
        self.key_widgets = {} 
        self.current_layout_name = self.layout_selector.get()
        self._draw_keyboard(self.layouts[self.current_layout_name])

        master.bind('<KeyPress>', self.on_key_press)
        master.bind('<KeyRelease>', self.on_key_release)
        master.bind('<FocusIn>', lambda e: master.focus_set()) # Asegurar que la ventana tiene el foco

    # --- Definiciones de Layouts ---
    def _get_common_special_keys(self):
        """Define las teclas de función y navegación comunes a ambos layouts."""
        return [
            # Fila de Funciones y Escape
            [("Escape", "Esc", 1), ("F1", "F1"), ("F2", "F2"), ("F3", "F3"), ("F4", "F4", 1.5), 
             ("F5", "F5"), ("F6", "F6"), ("F7", "F7"), ("F8", "F8", 1.5), 
             ("F9", "F9"), ("F10", "F10"), ("F11", "F11"), ("F12", "F12")],
            # Bloque de edición/Navegación
            [("Print", "PrtSc"), ("Scroll_Lock", "ScrLk"), ("Pause", "Pause", 1)], # Teclas especiales arriba
            [("Insert", "Ins"), ("Delete", "Del"), ("Home", "Home"), ("End", "End")],
            [("Prior", "PgUp"), ("Next", "PgDn")],
            # Flechas de Navegación
            [("", "", 1), ("", "", 1), ("Up", "↑"), ("", "", 1)], # Fila superior flechas
            [("Left", "←"), ("Down", "↓"), ("Right", "→")], # Fila inferior flechas
        ]
    
    def _get_qwerty_layout(self):
        """Layout QWERTY estándar (US/UK)."""
        layout = self._get_common_special_keys() + [
            # Fila 2 (Números y Backspace)
            [("grave", "~ `"), ("1", "1 !"), ("2", "2 @"), ("3", "3 #"), ("4", "4 $"), 
             ("5", "5 %"), ("6", "6 ^"), ("7", "7 &"), ("8", "8 *"), ("9", "9 ("), 
             ("0", "0 )"), ("minus", "- _"), ("equal", "= +"), ("BackSpace", "⌫ Backspace", 2)],
            # Fila 3 (QWERTY)
            [("Tab", "↹ Tab", 1.5), ("q", "Q"), ("w", "W"), ("e", "E"), ("r", "R"), 
             ("t", "T"), ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), 
             ("p", "P"), ("bracketleft", "[ {"), ("bracketright", "] }"), ("backslash", "\\ |", 1.5)],
            # Fila 4 (ASDF)
            [("Caps_Lock", "⇪ Caps", 1.75), ("A or a", "A"), ("s || S", "S"), ("d", "D"), ("f", "F"), 
             ("g", "G"), ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), 
             ("semicolon", "; :"), ("apostrophe", "' \""), ("Return", "⏎ Enter", 2.25)],
            # Fila 5 (Shift)
            [("Shift_L", "⇧ Shift", 2.25), ("z", "Z"), ("x", "X"), ("c", "C"), 
             ("v", "V"), ("b", "B"), ("n", "N"), ("m", "M"), ("comma", ", <"), 
             ("period", ". >"), ("slash", "/ ?"), ("Shift_R", "⇧ Shift", 2.75)],
            # Fila 6 (Control, Alt, Space)
            [("Control_L", "Ctrl", 1.25), ("Alt_L", "Alt", 1.25), ("space", "Espacio", 6.5), 
             ("Alt_R", "Alt", 1.25), ("Control_R", "Ctrl", 1.25)],
        ]
        return layout

    def _get_azerty_layout(self):
        """Layout AZERTY estándar (Francés)."""
        # Nota: El 'keysym' de Tkinter para letras y números es a menudo independiente del layout físico,
        # pero redefinimos el texto visible y la posición para simular AZERTY.
        layout = self._get_common_special_keys() + [
            # Fila 2 (Números y Backspace)
            [("twosuperior", "²"), ("ampersand", "1 &"), ("eacute", "2 é"), ("quotedbl", "3 \""), ("apostrophe", "4 '"), 
             ("parenleft", "5 ("), ("section", "6 -"), ("egrave", "7 è"), ("underscore", "8 _"), ("ccedilla", "9 ç"), 
             ("agrave", "0 à"), ("parenright", ")"), ("equal", "= +"), ("BackSpace", "⌫ Backspace", 2)],
            # Fila 3 (AZERTY)
            [("Tab", "↹ Tab", 1.5), ("a", "A"), ("z", "Z"), ("e", "E"), ("r", "R"), 
             ("t", "T"), ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), 
             ("p", "P"), ("dead_circumflex", "^"), ("dollar", "$ £"), ("asterisk", "*", 1.5)],
            # Fila 4 (QSDF)
            [("Caps_Lock", "⇪ Caps", 1.75), ("q", "Q"), ("s", "S"), ("d", "D"), ("f", "F"), 
             ("g", "G"), ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), 
             ("m", "M"), ("ugrave", "ù %"), ("Return", "⏎ Enter", 2.25)],
            # Fila 5 (Shift)
            [("Shift_L", "⇧ Shift", 2.25), ("less", "<"), ("w", "W"), ("x", "X"), ("c", "C"), 
             ("v", "V"), ("b", "B"), ("n", "N"), ("comma", ","), ("semicolon", ";"), 
             ("colon", ": /"), ("Shift_R", "⇧ Shift", 2.75)],
            # Fila 6 (Control, Alt, Space)
            [("Control_L", "Ctrl", 1.25), ("Alt_L", "Alt", 1.25), ("space", "Espacio", 6.5), 
             ("Alt_R", "Alt", 1.25), ("Control_R", "Ctrl", 1.25)],
        ]
        return layout

    # --- Funciones de Interfaz ---

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
            
    def _create_key_widget(self, parent, text, keysym, width_ratio=1):
        """Crea y posiciona un Label que representa una tecla."""
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
        
        self.key_widgets[keysym] = key_label
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

    # --- Manejo de Eventos de Teclado ---

    def on_key_press(self, event):
        """Maneja el evento de pulsación: pinta la tecla y registra el tiempo."""
        keysym = event.keysym
        
        # Registrar tiempo de pulsación
        self.key_press_times[keysym] = datetime.now()

        # Pintar la tecla activa
        if keysym in self.key_widgets:
            self.key_widgets[keysym].config(bg=self.active_color)

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
    # Usar el shebang si se va a ejecutar directamente en Linux
    # #!/usr/bin/env python3 
    app = KeyboardTester(root)
    root.mainloop()
