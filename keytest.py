#!/usr/bin/env python3
import tkinter as tk
from datetime import datetime
from tkinter import ttk
import tkinter.messagebox 
import threading
import time

# --- PYNPUT INTEGRATION ---
# Importar pynput para captura de eventos y supresión del sistema
try:
    from pynput import keyboard
except ImportError:
    print("ERROR: 'pynput' not installed. It is no possible supress some keys on the system.")
    
    # Crea un mock para evitar errores graves si pynput no está instalado
    class MockKeyboard:
        Key = type('Key', (object,), {'esc': 'Escape', 'cmd_l': 'Super_L', 'cmd_r': 'Super_R', 'print_screen': 'Print', 'caps_lock': 'Caps_Lock', 'num_lock': 'Num_Lock'})
        def Listener(self, *args, **kwargs): return self
        def start(self): pass
        def join(self): pass
        def stop(self): pass
        def is_alive(self): return True
    keyboard = MockKeyboard()
# --- END PYNPUT INTEGRATION ---


class KeyboardTester:
    """Aplicación que usa pynput en un hilo secundario para suprimir teclas del sistema
    y gestionar todos los eventos de teclado, con soporte para QWERTY y AZERTY."""
    
    def __init__(self, master):
        self.master = master
        master.title("Keyboard Tester (US / FRENCH) - Pynput Active")
        master.geometry("1100x750") 
        
        # --- Variables de estado ---
        self.key_press_times = {}
        self.pressed_keys = set()
        self.default_color = "gray80"
        self.active_color = "green"
        self.tested_color = "khaki1"
        self.tk_queue = [] # Cola para comunicar eventos desde el hilo de pynput
        
        # --- Configuración de Pynput (Mapeo de teclas especiales) ---
        # Mapea las teclas de pynput a los keysyms de Tkinter
        self.key_map = {
            keyboard.Key.alt_l: 'Alt_L',
            keyboard.Key.alt_r: 'Alt_R',
            keyboard.Key.ctrl_l: 'Control_L',
            keyboard.Key.ctrl_r: 'Control_R',
            keyboard.Key.shift_l: 'Shift_L',
            keyboard.Key.shift_r: 'Shift_R',
            keyboard.Key.cmd_l: 'Super_L', # Tecla Windows/Super Izquierda
            keyboard.Key.cmd_r: 'Super_R', # Tecla Windows/Super Derecha
            keyboard.Key.tab: 'Tab',
            keyboard.Key.caps_lock: 'Caps_Lock',
            keyboard.Key.backspace: 'BackSpace',
            keyboard.Key.enter: 'Return',
            keyboard.Key.space: 'space',
            keyboard.Key.print_screen: 'Print', # Tecla Print Screen
            keyboard.Key.delete: 'Delete',
            keyboard.Key.insert: 'Insert',
            keyboard.Key.menu: 'Menu',
            keyboard.Key.num_lock: 'Num_Lock',
            keyboard.Key.home: 'Home',
            keyboard.Key.end: 'End',
            keyboard.Key.page_up: 'Prior',
            keyboard.Key.page_down: 'Next',
            keyboard.Key.up: 'Up',
            keyboard.Key.down: 'Down',
            keyboard.Key.left: 'Left',
            keyboard.Key.right: 'Right',
            # ¡IMPORTANTE! 'Capsock' en tu layout debe ser 'Caps_Lock' para que el mapeo funcione.
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
        self.layout_selector.current(0)
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
        
        list_frame = ttk.Frame(latency_group)
        list_frame.pack(fill="both", expand=True)
        
        self.latency_listbox = tk.Listbox(list_frame, width=35, height=25, font=("Courier", 10))
        self.latency_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.latency_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.latency_listbox.config(yscrollcommand=scrollbar.set)
        
        # --- Información del Autor ---
        self.author_label = tk.Label(master, 
                                     text="By Andres V. a.k.a. 4vs3c", 
                                     font=("Arial", 8), 
                                     fg="gray50")
        self.author_label.pack(side="bottom", pady=5)
        
        # --- Inicialización y Eventos ---
        self.key_widgets = {} 
        self.current_layout_name = self.layout_selector.get()
        self._draw_keyboard(self.layouts[self.current_layout_name])

        # ELIMINAMOS los bindings de Tkinter para que pynput tome el control total y SÍ suprima las teclas.
        # master.bind('<KeyPress>', self.on_key_press)
        # master.bind('<KeyRelease>', self.on_key_release)
        # master.bind('<FocusIn>', lambda e: master.focus_set()) # Esta línea ya no es tan crítica

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
            # Para teclas alfanuméricas/símbolos, usa el carácter.
            # No se necesita keysym.lower()/upper() aquí, se maneja en el mapeo de widgets.
            return key.char if key.char is not None else str(key)
        elif isinstance(key, keyboard.Key):
            # Para teclas especiales, usa el mapeo del diccionario
            return self.key_map.get(key, str(key))
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
        # suppress=True es la clave para BLOQUEAR las funciones del sistema (Super, PrtSc)
        self.listener = keyboard.Listener(
            on_press=self.on_press_pynput,
            on_release=self.on_release_pynput,
            suppress=True  
        )
        # Ejecuta el listener en un hilo secundario
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
        # La lógica de mapeo mayús/minús ya fue simplificada:
        # Si la tecla es 'A', busca 'A'. Si no existe, busca 'a'.
        target_keysym = keysym
        if target_keysym not in self.key_widgets and target_keysym.lower() in self.key_widgets:
            target_keysym = target_keysym.lower()
        
        self.key_press_times[target_keysym] = datetime.now()

        if target_keysym in self.key_widgets:
            self.key_widgets[target_keysym].config(bg=self.active_color)
        
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
    # --- Definiciones de Layouts y Funciones de Interfaz (Resto sin cambios) ---
    # ---------------------------------------------------------------------

    def _get_common_special_keys(self):
        """Define las teclas de función y navegación comunes a ambos layouts."""
        return [
            # Tu layout fue simplificado aquí, pero lo mantengo así
            [] 
        ]
    
    def _get_qwerty_layout(self):
        """Layout QWERTY estándar (US/UK) con keysyms minúsculos para letras."""
        # Usaré el layout que proporcionaste, ajustando solo la tecla Num_Lock para que coincida con el mapeo
        layout = self._get_common_special_keys() + [
            # Fila de Funciones y Escape
            [("Escape", "Esc", 1.5), ("F1", "F1"), ("F2", "F2"), ("F3", "F3"), ("F4", "F4"), 
             ("F5", "F5"), ("F6", "F6"), ("F7", "F7"), ("F8", "F8"), 
             ("F9", "F9"), ("F10", "F10"), ("F11", "F11"), ("F12", "F12"),
             ("Num_Lock", "NumLk"),("Print", "PrtSc"), ("Scroll_Lock", "ScrLk"), ("Pause", "Pause")],
            # Fila 1 (Números y Backspace)
            [("grave", "~ `"), ("1", "1 !"), ("
