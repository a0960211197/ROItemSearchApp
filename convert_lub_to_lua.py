import subprocess
import os
import re
import shutil
# === 設定路徑 ===
GRFCL_EXE = r"APP\GrfCL.exe"
GRF_PATH = r"C:\Program Files (x86)\Gravity\RagnarokOnline\data.grf"
UNLUAC_JAR = r"APP\unluac.jar"
INPUT_FILE = r"data\LuaFiles514\Lua Files\EquipmentProperties\EquipmentProperties.lub"

OUTPUT_FOLDER = "data"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "EquipmentProperties.lua")

# === 從 GRF 解壓 LUB ===
def extract_lub_from_grf():
    if not os.path.exists(GRFCL_EXE):
        print(f" 找不到 GrfCL.exe：{GRFCL_EXE}")
        return False

    print(" 正在從 GRF 解壓 LUB 檔...")
    result = subprocess.run([
        GRFCL_EXE,
        "-open", GRF_PATH,
        "-extractFolder", "",
        "data\\LuaFiles514\\Lua Files\\EquipmentProperties\\EquipmentProperties.lub",
        "-exit"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(" 解壓失敗：")
        print(result.stderr)
        return False

    print(" 解壓完成")
    return True

# === 使用 unluac.jar 反編譯 ===
def run_unluac(lub_file, lua_file):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(lua_file, "w", encoding="utf-8") as out:
        subprocess.run(["java", "-jar", UNLUAC_JAR, lub_file], stdout=out, stderr=subprocess.DEVNULL)

# === 清理格式 ===
def split_local_variables(code):
    pattern = re.compile(r'^(\s*)local\s+([\w\s,]+?)\s*=\s*([^\n]+)$', re.MULTILINE)
    def replacer(match):
        indent = match.group(1)
        var_str = match.group(2)
        val_str = match.group(3)
        vars = [v.strip() for v in var_str.split(',')]
        vals = [v.strip() for v in val_str.split(',')]
        lines = []
        for i, var in enumerate(vars):
            val = vals[i] if i < len(vals) else 'nil'
            lines.append(f"{indent}local {var} = {val}")
        return '\n'.join(lines)
    return pattern.sub(replacer, code)

def flatten_array_fields(code):
    pattern = re.compile(r'^(\s*)(\w+)\s*=\s*\{\s*\n((?:\s*\d+\s*,?\n)+)(\s*)\}', re.MULTILINE)
    def replacer(match):
        indent = match.group(1)
        key = match.group(2)
        values_block = match.group(3)
        values = [v.strip().strip(',') for v in values_block.strip().splitlines() if v.strip()]
        flat = ', '.join(values)
        return f"{indent}{key} = {{ {flat} }}"
    return pattern.sub(replacer, code)

def clean_lua_format(lua_file):
    with open(lua_file, "r", encoding="utf-8") as f:
        code = f.read()
    code = split_local_variables(code)
    code = flatten_array_fields(code)
     # ✅ 新增：移除不需要的區塊
    code = remove_specific_blocks(code, ["SkillGroup", "RefiningBonus", "GradeBonus"])
    with open(lua_file, "w", encoding="utf-8") as f:
        f.write(code)

def remove_specific_blocks(code, block_names):
    for name in block_names:
        # 移除整個形如：Name = { ... } 的區塊（非巢狀處理）
        pattern = re.compile(rf'{name}\s*=\s*\{{.*?\n\}}', re.DOTALL)
        code = pattern.sub('', code)
    return code


# === 主程序入口 ===
if __name__ == "__main__":
    if not extract_lub_from_grf():
        pass  # 已顯示錯誤
    elif not os.path.exists(INPUT_FILE):
        print(f" 找不到檔案: {INPUT_FILE}")
    elif not os.path.exists(UNLUAC_JAR):
        print(f" 找不到 unluac.jar，請放在 APP 資料夾中")
    else:
        print(" 正在反編譯...")
        run_unluac(INPUT_FILE, OUTPUT_FILE)
        print(" 正在整理格式...")
        clean_lua_format(OUTPUT_FILE)
        print(f" 輸出完成：{OUTPUT_FILE}")

    # 最後刪除解壓出的 LuaFiles514 資料夾
    TEMP_FOLDER = os.path.join("data", "LuaFiles514")
    if os.path.exists(TEMP_FOLDER):
        try:
            shutil.rmtree(TEMP_FOLDER)
            print(f" 已刪除暫存資料夾：{TEMP_FOLDER}")
        except Exception as e:
            print(f" 刪除暫存資料夾失敗：{e}")

