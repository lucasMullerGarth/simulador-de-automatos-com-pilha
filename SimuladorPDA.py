import tkinter as tk
from tkinter import ttk, messagebox
import re
import sys

# Aumenta o limite de recursao
sys.setrecursionlimit(5000)

# Constantes globais
EPS = ''
DISPLAY_EPS = 'e'

def clean_str(s):
    """Remove espacos extras de uma string"""
    if s:
        return s.strip()
    return ""

def parse_list(input_string):
    """Transforma string 'a, b' em lista ['a', 'b']"""
    if not input_string:
        return []
    parts = [clean_str(p) for p in input_string.split(',')]
    symbols = []
    for p in parts:
        if not p:
            continue
        if p.lower() == 'epsilon':
            continue
        symbols.append(p)
    # Remove duplicatas mantendo a ordem
    seen = set()
    res = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res

def parse_transitions(input_text):
    """Faz o parsing das regras de transicao"""
    if not isinstance(input_text, str):
        return {}
    
    transitions = {}
    lines = [l.strip() for l in input_text.strip().splitlines() if l.strip()]
    
    # Regex para capturar: origem, entrada, topo -> destino, push
    pattern = re.compile(r'^\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^\-]+)\s*->\s*([^,]+)\s*,\s*(.+)\s*$')

    for line in lines:
        m = pattern.match(line)
        if not m:
            continue
            
        origem, entrada, topo, destino, push_raw = m.groups()
        
        origem = clean_str(origem)
        destino = clean_str(destino)
        
        entrada_key = EPS if clean_str(entrada).lower() == 'epsilon' else clean_str(entrada)
        topo_key = EPS if clean_str(topo).lower() == 'epsilon' else clean_str(topo)
        
        push_str = clean_str(push_raw)
        
        # LOGICA DE PUSH INTELIGENTE
        if push_str.lower() == 'epsilon':
            push_list = []
        elif ',' in push_str or ' ' in push_str:
            normalized = push_str.replace(',', ' ')
            push_list = [clean_str(s) for s in normalized.split(' ') if clean_str(s)]
        else:
            push_list = re.findall(r'Z0|.', push_str)
            
        key = (origem, entrada_key, topo_key)
        val = (destino, push_list)
        
        if key not in transitions:
            transitions[key] = []
        transitions[key].append(val)
        
    return transitions

# Classe Config (Ramo)
class Config:
    def __init__(self, state, stack, input_index):
        self.state = state
        self.stack = list(stack)
        self.input_index = input_index

    def get_stack_top(self):
        if not self.stack:
            return EPS
        return self.stack[-1]

    def pop_stack(self):
        if self.stack:
            self.stack.pop()

    def push_stack(self, symbols):
        for sym in reversed(symbols):
            self.stack.append(sym)
            
    def __repr__(self):
        stk_str = " ".join(self.stack) if self.stack else "Vazia"
        return f"[{self.state}] Pilha: {stk_str}"

# Motor do Automato
class PushdownAutomaton:
    def __init__(self, states, input_alphabet, stack_alphabet, initial_state, final_states, transitions_dict, initial_stack_symbol):
        self.states = set(states)
        self.input_alphabet = set(input_alphabet)
        self.stack_alphabet = set(stack_alphabet)
        self.initial_state = initial_state
        self.final_states = set(final_states)
        self.transitions = transitions_dict
        self.initial_stack_symbol = initial_stack_symbol
        self.input_string = ""
        
        self.active_configs = [] 
        self.step_count = 0
        self.halted = False
        self.final_result = None 

    def validate_setup(self, input_string):
        """Verifica se a entrada e a pilha respeitam os alfabetos"""
        
        # 1. Verifica Alfabeto de Entrada
        for char in input_string:
            if char not in self.input_alphabet:
                return False, f"Erro: O símbolo '{char}' na entrada não pertence ao Alfabeto de Entrada."
        
        # 2. Verifica Símbolo Inicial da Pilha
        if self.initial_stack_symbol and self.initial_stack_symbol not in self.stack_alphabet:
            return False, f"Erro: O símbolo inicial da pilha '{self.initial_stack_symbol}' não pertence ao Alfabeto da Pilha."
            
        return True, "OK"

    def reset(self, input_string=""):
        self.input_string = input_string
        self.step_count = 0
        self.halted = False
        self.final_result = None
        
        start_stack = []
        if self.initial_stack_symbol:
            start_stack.append(self.initial_stack_symbol)
            
        initial_cfg = Config(self.initial_state, start_stack, 0)
        self.active_configs = [initial_cfg]

    def step(self):
        if self.halted:
            return self.final_result

        if not self.active_configs:
            self.halted = True
            self.final_result = 'rejected'
            return 'rejected'

        if self.check_acceptance():
            self.halted = True
            self.final_result = 'accepted'
            return 'accepted'

        next_configs = []
        
        for cfg in self.active_configs:
            state = cfg.state
            top = cfg.get_stack_top()
            
            if cfg.input_index < len(self.input_string):
                inp = self.input_string[cfg.input_index]
            else:
                inp = EPS

            possible_moves = []
            
            # Movimentos
            if inp != EPS:
                key = (state, inp, top)
                if key in self.transitions:
                    for dest, push_seq in self.transitions[key]:
                        possible_moves.append((dest, push_seq, True))

            key_eps = (state, EPS, top)
            if key_eps in self.transitions:
                for dest, push_seq in self.transitions[key_eps]:
                    possible_moves.append((dest, push_seq, False))

            for dest, push_seq, consumed in possible_moves:
                new_cfg = Config(state, cfg.stack, cfg.input_index)
                if top != EPS: new_cfg.pop_stack()
                new_cfg.push_stack(push_seq)
                new_cfg.state = dest
                if consumed: new_cfg.input_index += 1
                next_configs.append(new_cfg)

        # Otimizacao e Limpeza
        unique_configs = []
        seen_configs = set()
        for c in next_configs:
            rep = (c.state, c.input_index, tuple(c.stack))
            if rep not in seen_configs:
                seen_configs.add(rep)
                unique_configs.append(c)
        
        if len(unique_configs) > 100:
            unique_configs = unique_configs[:100]
            
        self.active_configs = unique_configs
        self.step_count += 1

        if self.check_acceptance():
            self.halted = True
            self.final_result = 'accepted'
            return 'accepted'
        
        if not self.active_configs:
            self.halted = True
            self.final_result = 'rejected'
            return 'rejected'

        return 'running'

    def check_acceptance(self):
        for cfg in self.active_configs:
            input_consumed = (cfg.input_index >= len(self.input_string))
            is_final = (cfg.state in self.final_states)
            if input_consumed and is_final:
                return True
        return False

    def get_status_str(self):
        count = len(self.active_configs)
        if count == 0: return "Nenhum caminho ativo."
        details = []
        for i, c in enumerate(self.active_configs[:5]):
            rem = self.input_string[c.input_index:] if c.input_index < len(self.input_string) else "e"
            stk = " ".join(c.stack) if c.stack else "e"
            details.append(f"Ramo {i+1}: Est={c.state} | Pilha={stk} | Rest={rem}")
        if count > 5: details.append(f"... (+ {count-5} outros)")
        return "\n".join(details)

# Interface Grafica
class SimGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador PDA Final")
        self.pda = None
        self._setup_ui()
        
    def _setup_ui(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        
        # 1. Estados
        self._create_field(frame, 0, "Estados (ex: q0,q1):", "q0,q1,q2,qf")
        self.entry_states = self.last_entry
        
        # 2. Alfabetos (NOVOS CAMPOS)
        self._create_field(frame, 1, "Alfabeto Entrada (ex: a,b):", "a,b,c")
        self.entry_in_alpha = self.last_entry
        
        self._create_field(frame, 2, "Alfabeto Pilha (ex: Z0,A):", "Z0")
        self.entry_stack_alpha = self.last_entry
        
        # 3. Configuracoes Iniciais
        self._create_field(frame, 3, "Estado Inicial:", "q0")
        self.entry_initial = self.last_entry
        
        self._create_field(frame, 4, "Estados Finais:", "qf")
        self.entry_finals = self.last_entry
        
        self._create_field(frame, 5, "Simbolo Inicial Pilha:", "Z0")
        self.entry_stack_init = self.last_entry
        
        # 4. Transicoes
        ttk.Label(frame, text="Transicoes:").grid(row=6, column=0, sticky="nw")
        self.text_trans = tk.Text(frame, height=8, width=45)
        self.text_trans.grid(row=6, column=1, pady=5)
        
        # Exemplo padrao nao-deterministico (abc)
        ex_text = ("q0, a, Z0 -> q1, Z0\n"
                   "q0, a, Z0 -> q2, Z0\n"
                   "q1, b, Z0 -> q1, Z0\n"
                   "q1, c, Z0 -> qf, Z0\n"
                   "q2, c, Z0 -> q2, Z0")
        self.text_trans.insert("1.0", ex_text)
        
        # 5. Entrada
        self._create_field(frame, 7, "Entrada para teste:", "abc")
        self.entry_input = self.last_entry
        
        # 6. Botoes
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Carregar / Validar", command=self.load_pda).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Proximo Passo", command=self.step).pack(side="left", padx=5)

        # 7. Status e Monitoramento
        self.lbl_result = ttk.Label(frame, text="Status: Aguardando", font=("Arial", 10, "bold"))
        self.lbl_result.grid(row=9, column=0, columnspan=2, pady=5)
        
        self.lbl_step_count = ttk.Label(frame, text="Passo: 0")
        self.lbl_step_count.grid(row=10, column=0, columnspan=2, sticky="w")
        
        lbl_info = ttk.Label(frame, text="Caminhos Ativos (Multi-Ramos):")
        lbl_info.grid(row=11, column=0, sticky="nw", pady=(10,0))
        
        self.lbl_details = tk.Label(frame, text="-", justify="left", bg="white", relief="sunken", anchor="nw")
        self.lbl_details.grid(row=12, column=0, columnspan=2, sticky="nsew", ipady=10)
        
    def _create_field(self, parent, row, label, default):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(parent, width=30)
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="ew")
        self.last_entry = entry

    def load_pda(self):
        try:
            # Captura todos os campos
            states = parse_list(self.entry_states.get())
            in_alpha = parse_list(self.entry_in_alpha.get())
            stack_alpha = parse_list(self.entry_stack_alpha.get())
            initial = self.entry_initial.get().strip()
            finals = parse_list(self.entry_finals.get())
            stack_init = self.entry_stack_init.get().strip()
            input_str = self.entry_input.get().strip()
            
            trans_txt = self.text_trans.get("1.0", tk.END)
            transitions = parse_transitions(trans_txt)
            
            # Instancia o PDA
            self.pda = PushdownAutomaton(states, in_alpha, stack_alpha, initial, finals, transitions, stack_init)
            
            # Valida Alfabetos
            is_valid, msg_error = self.pda.validate_setup(input_str)
            if not is_valid:
                messagebox.showerror("Erro de Validação", msg_error)
                self.pda = None # Anula o PDA invalido
                self.update_display("Erro na definição.", "red")
                return

            # Se validou, reseta e prepara
            self.pda.reset(input_str)
            self.update_display("Carregado e Validado.", "blue")
            
        except Exception as e:
            messagebox.showerror("Erro Crítico", str(e))

    def step(self):
        if not self.pda:
            messagebox.showwarning("Aviso", "Carregue o autômato primeiro.")
            return
        
        res = self.pda.step()
        
        if res == 'accepted':
            self.update_display("ACEITO!", "green")
            messagebox.showinfo("Sucesso", "A entrada foi ACEITA!")
        elif res == 'rejected':
            self.update_display("REJEITADO (Todos caminhos falharam)", "red")
        else:
            self.update_display("Executando...", "blue")

    def update_display(self, status, color):
        self.lbl_result.config(text=status, foreground=color)
        if self.pda:
            self.lbl_step_count.config(text=f"Passo: {self.pda.step_count}")
            self.lbl_details.config(text=self.pda.get_status_str())
        else:
            self.lbl_details.config(text="-")

def main():
    root = tk.Tk()
    app = SimGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()