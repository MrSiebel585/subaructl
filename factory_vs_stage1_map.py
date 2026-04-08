import os
from colorama import Fore, Style, init

init(autoreset=True)

# Updated Configuration
MAP_MASTER = "/opt/maps/impreza_basemap_tune.bin"
MAP_STAGE = "/opt/maps/impreza_basemap_stage_ecuflash_model.bin"

# A4TF800F 160KB calibration sectors
MAPS = {
    0x22000: "Fueling (AFR Targets)",
    0x22600: "Ignition (Spark Advance)",
    0x22A00: "Target Boost (PSI)",
    0x22C00: "Wastegate Duty (Turbo Control)"
}

def run_audit():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}[OMNISCIENT] :: STAGE 1 PERFORMANCE DELTA")
    print(f"{Fore.WHITE}Comparing Master Baseline to Stage 1 Model\n")
    
    for path in [MAP_MASTER, MAP_STAGE]:
        if not os.path.exists(path):
            print(f"{Fore.RED}Error: File not found: {path}")
            return

    with open(MAP_MASTER, 'rb') as f_m, open(MAP_STAGE, 'rb') as f_s:
        master = f_m.read()
        stage = f_s.read()

    print(f"{Fore.WHITE}{'OFFSET':<12} | {'MASTER':<8} | {'STAGE 1':<8} | {'SECTOR'}")
    print("-" * 65)

    diff_count = 0
    # Scan the tuning window
    for i in range(0x22000, len(master)):
        if master[i] != stage[i]:
            addr = hex(i).upper().replace("0X", "0x")
            v_mast = hex(master[i]).upper().replace("0X", "0x").zfill(4)
            v_stage = hex(stage[i]).upper().replace("0X", "0x").zfill(4)
            
            sector = "Calibration Data"
            for offset, label in MAPS.items():
                if offset <= i <= (offset + 0x3FF):
                    sector = label
                    break
            
            # Print logic: Highlight Stage 1 improvements
            print(f"{Fore.CYAN}{addr:<12} {Fore.WHITE}| "
                  f"{Fore.WHITE}{v_mast:<8} {Fore.WHITE}| "
                  f"{Fore.GREEN}{v_stage:<8} {Fore.WHITE}| "
                  f"{Fore.YELLOW}{sector}")
            
            diff_count += 1
            if diff_count >= 50: break

    if diff_count == 0:
        print(f"{Fore.YELLOW}No differences found. The Stage 1 file matches the Master.")
    else:
        print(f"\n{Fore.GREEN}Audit Complete. Found {diff_count} performance tweaks.")
        print(f"{Fore.MAGENTA}Note: Higher hex in Ignition/Boost = More Power.")

if __name__ == "__main__":
    run_audit()
