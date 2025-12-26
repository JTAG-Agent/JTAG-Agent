import subprocess
import os
import signal
import time
from pygdbmi.gdbcontroller import GdbController

class GDBInterface:
    def __init__(self, elf_path="firmware/app.elf"):
        self.elf_path = elf_path
        self.qemu_proc = None
        self.gdbmi = None

    def start(self):
        """Ensures the environment is running."""
        if not self.gdbmi:
            self.restart_environment()

    def restart_environment(self):
        """Kills existing sessions and starts fresh from the first instruction."""
        self.stop_all()
        
        # 1. Start QEMU in the background
        # We use setsid to manage the process group
        self.qemu_proc = subprocess.Popen(
            ["make", "startqemu"], 
            preexec_fn=os.setsid,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Give QEMU a moment to bind to port 1234
        time.sleep(1) 
        
        # 2. Start GDB via pygdbmi
        self.gdbmi = GdbController(["gdb-multiarch", "-q", "--interpreter=mi3"])
        self.gdbmi.write(f"-file-exec-and-symbols {self.elf_path}")
        self.gdbmi.write("target remote localhost:1234")
        
        return "Environment restarted. CPU is halted at entry point."

    def stop_all(self):
        """Cleanly kill processes."""
        if self.qemu_proc:
            os.killpg(os.getpgid(self.qemu_proc.pid), signal.SIGTERM)
            self.qemu_proc = None
        if self.gdbmi:
            self.gdbmi.exit()
            self.gdbmi = None

    def step_instruction(self):
        """Executes exactly one instruction (stepi)."""
        # -exec-step is for source lines, -exec-next-instruction is for ASM
        response = self.gdbmi.write("-exec-next-instruction")
        return response

    def continue_execution(self):
        """Continues execution until a breakpoint is hit or the program stops."""
        response = self.gdbmi.write("-exec-continue")
        return response

    def get_registers(self):
        """Reads all general purpose registers."""
        # 'x' stands for hexadecimal format
        response = self.gdbmi.write("-data-list-register-values x")
        return response

    def read_memory(self, address: str, length: int):
        """Reads memory bytes from a specific address. Address should be a hex string (e.g. '0x8000')."""
        response = self.gdbmi.write(f"-data-read-memory-bytes {address} {length}")
        return response

    def set_breakpoint(self, location: str):
        """Sets a breakpoint at a function name or address (e.g. 'main' or '*0x08000100')."""
        response = self.gdbmi.write(f"-break-insert {location}")
        return response

    def backtrace(self):
        """Gets the current stack trace to see the call stack."""
        response = self.gdbmi.write("-stack-list-frames")
        return response

    def evaluate_expression(self, expression: str):
        """Evaluates a C expression or variable value (e.g. 'my_variable')."""
        response = self.gdbmi.write(f'-data-evaluate-expression "{expression}"')
        return response

    def write_register(self, register_name: str, value: str):
        """Writes a value to a CPU register (e.g. 'R0', 'PC'). Value should be hex string."""
        response = self.gdbmi.write(f'-gdb-set ${register_name}={value}')
        return response

    def write_memory(self, address: str, value: str, width: int = 4):
        """Writes a value to memory. Width is bytes (1, 2, 4)."""
        # GDB MI doesn't have a simple write-memory command, so we use console
        type_map = {1: "char", 2: "short", 4: "int", 8: "long long"}
        c_type = type_map.get(width, "int")
        cmd = f'set *({c_type}*){address} = {value}'
        response = self.gdbmi.write(f'-interpreter-exec console "{cmd}"')
        return response
    
    def write_register(self, register_id: str, value: str):
        """Sets a specific register to a value. register_id is the name or number, value is hex (e.g., '0x1')."""
        # Example: -gdb-set $pc = 0x80000000
        # For registers, GDB MI usually uses -gdb-set
        response = self.gdbmi.write(f"-gdb-set ${register_id} = {value}")
        return response

    def write_memory(self, address: str, value: str):
        """Writes a hex value to a specific memory address (e.g., address='0x20000000', value='0xAA55')."""
        # Uses GDB's set {type}addr = value syntax via the MI
        # We wrap it in a CLI command for simplicity as MI memory write can be picky
        response = self.gdbmi.write(f'interpreter-exec console "set {{int}}{address} = {value}"')
        return response