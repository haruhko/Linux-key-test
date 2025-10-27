#!/usr/bin/env python3
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from pynput import keyboard
import threading
import tkinter.messagebox # Importar para usar en el hilo principal

class KeyboardTester:
    """Aplicación de testeo de teclado con hooking de bajo nivel (pynput)."""
    
    def __init__(self, master):
        self.master = master
        master.title("Testeador de Teclado (Rendimiento Mejorado y Bloqueo)")
        master.geometry("1050x700")
        
        # --- Variables de estado ---
        self.key_press_times = {}
        self.pressed_keys = set()
        self.default_color = "gray80"
        self.active_color = "green"
        self.tested_color = "khaki1"
        self.listener = None
        self.tk_queue = [] # Cola para comunicar eventos de pynput a Tkinter

        # --- Definición de Layouts (Mismos que el script anterior) ---
        self.layouts = {
            "Inglés (QWERTY)": self._get_qwerty_layout(),
            "Francés (AZERTY)": self._get_azerty_layout(),
        }

        # --- Interfaz Gráfica (Misma estructura) ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 1. Controles y Botón de Reset
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)

        ttk.Label(control_frame, text="Selecciona Distribución:").pack(side="left", padx=5)
        
        self.layout_selector = ttk.Combobox(
            control_frame, 
            values=list(self.layouts.keys()), 
            state="readonly",
            width=20
        )
        self.layout_selector.current(0)
        self.layout_selector.bind("<<ComboboxSelected>>", self.switch_layout)
        self.layout_selector.pack(side="left", padx=10)

        # Botón de Reset
        ttk.Button(control_frame, text="🔁 Resetear Teclas Testeadas", command=self.reset_tested_keys).pack(side="right")
        
        # 2. Contenedor Principal (Teclado + Lista)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        # 2.1. Zona del Teclado (Izquierda)
        self.keyboard_frame = ttk.LabelFrame(content_frame, text="Teclado Visual", padding="5")
        self.keyboard_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # 2.2. Zona de Latencias (Derecha)
        latency_group = ttk.LabelFrame(content_frame, text="Latencias Registradas (ms)", padding="10")
        latency_group.pack(side="right", fill="y", padx=10)
        
        list_frame = ttk.Frame(latency_group)
        list_frame.pack(fill="both", expand=True)
        
        self.latency_listbox = tk.Listbox(list_frame, width=35, height=25, font=("Courier", 10))
        self.latency_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.latency_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.latency_listbox.config(yscrollcommand=scrollbar.set)
        
        # --- Inicialización y Hooking ---
        self.key_widgets = {} 
        self.current_layout_name = self.layout_selector.get()
        self._draw_keyboard(self.layouts[self.current_layout_name])

        # 3. Inicializar pynput Listener en un hilo separado
        self._start_keyboard_listener()
        
        # 4. Iniciar polling con un intervalo más rápido para mejorar la respuesta
        # Se redujo de 100ms a 10ms (más responsivo)
        self.master.after(10, self.process_tk_queue) 
        
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # -----------------------------------------------------------------------------------
    # --- Lógica de Manejo de Eventos (Pynput) ---
    # -----------------------------------------------------------------------------------

    def _get_keysym(self, key):
        """Intenta obtener el keysym de pynput de forma robusta."""
        try:
            # Para teclas alfanuméricas
            return key.char
        except AttributeError:
            # Para teclas especiales
            if key == keyboard.Key.space: return 'space'
            if key == keyboard.Key.backspace: return 'BackSpace'
            if key == keyboard.Key.enter: return 'Return' # Tkinter keysym for Enter
            if key == keyboard.Key.esc: return 'Escape'
            if key == keyboard.Key.tab: return 'Tab'
            if key == keyboard.Key.caps_lock: return 'Caps_Lock'
            if key == keyboard.Key.shift_l: return 'Shift_L'
            if key == keyboard.Key.shift_r: return 'Shift_R'
            if key == keyboard.Key.ctrl_l: return 'Control_L'
            if key == keyboard.Key.ctrl_r: return 'Control_R'
            if key == keyboard.Key.alt_l: return 'Alt_L'
            if key == keyboard.Key.alt_r: return 'Alt_R'
            if key == keyboard.Key.cmd_l: return 'Super_L' # Tecla Super/Windows/Comando
            if key == keyboard.Key.cmd_r: return 'Super_R'
            if key == keyboard.Key.insert: return 'Insert'
            if key == keyboard.Key.delete: return 'Delete'
            # Mapeo de teclas de función y navegación
            try:
                # Tratar de mapear las flechas y F keys que pynput nombra
                return str(key).split('.')[-1]
            except:
                return str(key) # Retorno por defecto de pynput
            
    def _is_key_critical(self, keysym):
        """Verifica si la tecla es crítica y debe ser bloqueada del SO."""
        # Se incluyen las teclas Super (Windows/Cmd) y Print_Screen explícitamente.
        return keysym in self.key_widgets or keysym in ['Super_L', 'Super_R', 'Print_Screen', 'Escape']

    def _on_key_press_pynput(self, key):
        """Callback de pynput para la pulsación de tecla."""
        keysym = self._get_keysym(key)
        
        # 1. Enviar el evento a la cola de Tkinter
        self.tk_queue.append(('press', keysym))
        
        # 2. Bloqueo estricto: Si es una tecla crítica (incluyendo Super), la bloqueamos.
        # Si el keysym está en nuestro layout, también se bloquea.
        if self._is_key_critical(keysym):
            return False # Bloquear la propagación al SO
        
        return True # Permitir la propagación al SO para otras teclas

    def _on_key_release_pynput(self, key):
        """Callback de pynput para la liberación de tecla."""
        keysym = self._get_keysym(key)
        self.tk_queue.append(('release', keysym))
        
        # También bloqueamos la liberación de teclas críticas para asegurar el control.
        if self._is_key_critical(keysym):
            return False
            
        return True 

    def _start_keyboard_listener(self):
        """Inicia el listener de pynput en un hilo separado."""
        self.listener = keyboard.Listener(
            on_press=self._on_key_press_pynput,
            on_release=self._on_key_release_pynput
        )
        # Usar daemon=True asegura que el hilo se cerrará con la aplicación principal
        self.listener.daemon = True 
        self.listener.start()

    def process_tk_queue(self):
        """Procesa los eventos de la cola en el hilo principal de Tkinter."""
        # Procesamos hasta 50 eventos por ciclo para evitar que el bucle de la GUI se congele.
        processed_count = 0
        while self.tk_queue and processed_count < 50: 
            event_type, keysym = self.tk_queue.pop(0)
            
            if event_type == 'press':
                self._handle_tk_press(keysym)
            elif event_type == 'release':
                self._handle_tk_release(keysym)
            
            processed_count += 1
                
        # Continuar el polling con el mismo intervalo rápido (10ms)
        self.master.after(10, self.process_tk_queue) 

    # -----------------------------------------------------------------------------------
    # --- Resto de las Funciones (GUI, Layouts) (SIN CAMBIOS) ---
    # -----------------------------------------------------------------------------------
    
    # [Funciones _handle_tk_press, _handle_tk_release, on_closing, 
    #  switch_layout, reset_tested_keys, etc. permanecen iguales al script anterior]
    
    def _handle_tk_press(self, keysym):
        """Actualiza la GUI para la pulsación de tecla."""
        self.key_press_times[keysym] = datetime.now()
        if keysym in self.key_widgets:
            self.key_widgets[keysym].config(bg=self.active_color)
            
    def _handle_tk_release(self, keysym):
        """Actualiza la GUI para la liberación de tecla y calcula latencia."""
        if keysym in self.key_press_times:
            press_time = self.key_press_times.pop(keysym)
            release_time = datetime.now()
            latency_ms = (release_time - press_time).total_seconds() * 1000
            latency_text = f"[{keysym:^15}]: {latency_ms:7.2f} ms"
            self.latency_listbox.insert(0, latency_text) 
            
        if keysym in self.key_widgets:
            self.pressed_keys.add(keysym)
            self.key_widgets[keysym].config(bg=self.tested_color)
            
    def on_closing(self):
        """Detiene el listener de pynput al cerrar la aplicación."""
        if self.listener:
            self.listener.stop()
        self.master.destroy()
        
    def reset_tested_keys(self):
        """Reinicia el estado de las teclas testeadas (color amarillo)."""
        if not tkinter.messagebox.askyesno("Confirmar Reset", "¿Estás seguro de que quieres resetear el estado de todas las teclas testeadas?"):
            return

        self.pressed_keys.clear()
        self.key_press_times.clear()
        self.latency_listbox.delete(0, tk.END)
        
        for widget in self.key_widgets.values():
            widget.config(bg=self.default_color)
        
        tkinter.messagebox.showinfo("Reset Completo", "El estado de las teclas y el historial de latencias han sido reseteados.")

    def _clear_keyboard_frame(self):
        for widget in self.keyboard_frame.winfo_children():
            widget.destroy()
        self.key_widgets = {}

    def switch_layout(self, event):
        new_layout_name = self.layout_selector.get()
        if new_layout_name != self.current_layout_name:
            self.current_layout_name = new_layout_name
            self._clear_keyboard_frame()
            self._draw_keyboard(self.layouts[new_layout_name])
            self._restore_tested_colors()
            
    def _restore_tested_colors(self):
        for keysym in self.pressed_keys:
             if keysym in self.key_widgets:
                self.key_widgets[keysym].config(bg=self.tested_color)
                
    def _create_key_widget(self, parent, text, keysym, width_ratio=1):
        width = int(5 * width_ratio) 
        initial_color = self.tested_color if keysym in self.pressed_keys else self.default_color
        key_label = tk.Label(parent, text=text, bg=initial_color, relief="raised", borderwidth=2,
                             width=width, height=2, font=("Arial", 10, "bold"))
        self.key_widgets[keysym] = key_label
        return key_label

    def _draw_keyboard(self, layout):
        for r_index, row in enumerate(layout):
            row_frame = ttk.Frame(self.keyboard_frame)
            row_frame.pack(fill="x
