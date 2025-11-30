import re
import subprocess
import tkinter as tk
from tkinter import filedialog
import os
import json
import importlib.util
# ======【設定區】======
SHOW_OFFSET = False# 顯示 slot 在 group 內的 offset 位置
SHOW_RAW = False# 顯示 slot 的原始 bytes（每8顆一行）
SHOW_2201 = True# 顯示 2201 slot 卡片解析
SHOW_2301 = True# 顯示 2301 slot 裝備解析
SHOW_2701 = True# 顯示 2701 slot 解析（精煉等級）
SHOW_2D01 = True# 顯示 2D01 slot 附魔解析
SHOW_2B01 = True# 顯示 2B01 slot 裝備階級
SHOW_GROUPS = []#只顯示指定的 group編號，空列表/None代表顯示全部，如 [1,3] 只顯示第1和第3個group
SHOW_GROUP_NAMES = []# 例如 ['頭下', '盾牌'] 只顯示這兩個部位, 空的話全部顯示
SHOW_ONLY_FILLED = True     # 只顯示有資料的部位（group）
SHOW_ONLY_PARSED_SLOTS = True   # 只顯示有解析/開關開啟的 slot
# ======================
GRADE_MAP = {
    0: "N",
    1: "D",
    2: "C",
    3: "B",
    4: "A"
}
GROUP_NAME_MAP = {
    1: '頭下',
    2: '右手(武器)',
    3: '披肩',
    4: '飾品右',
    5: '鎧甲',
    6: '左手(盾牌)',
    7: '鞋子',
    8: '飾品左',
    9: '頭上',
    10: '頭中',
}
Shadow_GROUP_NAME_MAP = {

    1: '服飾頭下',
    2: '影子手套',
    3: '服飾斗篷',
    4: '影子耳環右',
    5: '影子鎧甲',
    6: '影子盾牌',
    7: '影子鞋子',
    8: '影子墬子左',
    9: '服飾頭上',
    10: '服飾頭中',
}


def load_python_dict(path, var_name):
    """
    從外部 .py 檔載入指定變數。
    
    path: 外部 .py 檔案路徑
    var_name: 要讀取的 dict 變數名稱，例如 'all_skill_entries'
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"外部資料檔不存在: {path}")

    spec = importlib.util.spec_from_file_location("external_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, var_name):
        raise AttributeError(f"{path} 裡找不到變數: {var_name}")

    return getattr(module, var_name)


job_dict = load_python_dict("data/job_dict.py", "job_dict")#職業job_id


import sys, os
def resource_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)


# 載入EnumVAR.lua
with open("data/enumvar.lua", "r", encoding="utf-8") as f:
    enum_lua = f.read()

# 解析 EnumVAR：104 -> RACE_DAMAGE_HUMAN
id_to_key = {}
enumvar_pat = re.compile(r'(\w+)\s*=\s*{\s*(\d+)\s*,\s*(\d+)\s*}', re.MULTILINE)
for m in enumvar_pat.finditer(enum_lua):
    key, k1, k2 = m.group(1), int(m.group(2)), int(m.group(3))
    id_to_key[k1] = key
    # 部分表格反著也要支援，像 { 104, 7 } ，附魔ID 104、value 7


# 讀 AddRandomOptionNameTable.lua
with open("data/AddRandomOptionNameTable.lua", "r", encoding="utf-8") as f:
    addopt_lua = f.read()

# EnumVAR.KEY[1] = "中文描述"
key_to_desc = {}
desc_pat = re.compile(r'\[EnumVAR\.([A-Z0-9_]+)\[1\]\]\s*=\s*"([^"]+)"')
for m in desc_pat.finditer(addopt_lua):
    key = m.group(1)  # EnumVAR 名稱
    desc = m.group(2)
    key_to_desc[key] = desc

with open("data/EnchantName.lua", "r", encoding="utf-8") as f:
    enchant_lua = f.read()

key_to_jsonfmt = {}
json_pat = re.compile(r'\[EnumVAR\.([A-Z0-9_]+)\[1\]\]\s*=\s*"([^"]+)"')
for m in json_pat.finditer(enchant_lua):
    key = m.group(1)
    fmt = m.group(2)
    key_to_jsonfmt[key] = fmt




def get_enchant_info(enchant_id, value):
    """
    return: (顯示用中文, JSON用格式字串)
    """

    # Step1: 找 enumvar key 名稱
    key = id_to_key.get(enchant_id)
    if not key:
        return ("", "")   # 無附魔 or 不支援 ID

    # Step2: 找中文附魔描述
    desc_fmt = key_to_desc.get(key, "")
    if desc_fmt:
        try:
            desc_text = desc_fmt % value
        except:
            desc_text = f"{desc_fmt} ({value})"
    else:
        desc_text = f"{key} +{value}"

    # Step3: 找 JSON 格式 (AddExtParam...)
    json_fmt = key_to_jsonfmt.get(key, "")
    if json_fmt:
        json_text = json_fmt.replace("%d", str(value))
    else:
        json_text = ""

    return (desc_text, json_text)



# ================================================================
# 你的 iteminfo parser（照你給的保留）
# ================================================================
def parse_lub_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        QMessageBox.critical(None, "錯誤", f"找不到檔案：{filename}")
        return {}

    item_entries = re.findall(
        r"\[(\d+)\]\s*=\s*{(.*?)}(?=,\s*\[\d+\]|\s*\[\d+\]|\s*$)",
        content,
        re.DOTALL
    )

    parsed_items = {}
    for item_id, body in item_entries:
        try:
            item_id = int(item_id)

            identified_name = re.search(r'(?<!un)identifiedDisplayName\s*=\s*"([^"]+)"', body)
            kr_name = re.search(r'(?<!un)identifiedResourceName\s*=\s*"([^"]+)"', body)
            slot = re.search(r'slotCount\s*=\s*(\d+)', body)

            # 描述
            desc_match = re.search(r'(?<!un)identifiedDescriptionName\s*=\s*{(.*?)}', body, re.DOTALL)
            if desc_match:
                desc_body = desc_match.group(1)
                desc_lines_raw = re.findall(r'"([^"]*)"', desc_body)
                desc_lines = [line.strip() for line in desc_lines_raw]
            else:
                desc_lines = []

            if identified_name and kr_name and slot:
                base_name = identified_name.group(1).strip()
                slot_count = int(slot.group(1))

                display_name = f"{base_name} [{slot_count}]" if slot_count > 0 else base_name

                parsed_items[item_id] = {
                    "name": display_name,
                    "base_name": base_name,
                    "kr_name": kr_name.group(1).strip(),
                    "description": desc_lines,
                    "slot": slot_count
                }

        except:
            pass

    return parsed_items

def parse_equipment_blocks(content):
    import re

    blocks = {}
    pattern = re.compile(r"\[(\d+)\]\s*=\s*{", re.MULTILINE)
    matches = list(pattern.finditer(content))
    total = len(matches)
    #print(f"📦 開始解析裝備區塊，共 {total} 筆資料")

    for i, match in enumerate(matches):
        item_id = int(match.group(1))
        start = match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(content)

        block_text = content[start:end].strip()

        # 加回完整大括號包裹，確保 block 格式正確
        block_text_full = "{" + block_text.rstrip(",") + "}"

        blocks[item_id] = block_text_full
        #print(f"  → 處理中 {i+1}/{total} 筆", end="\r")
    #print(f"\n✅ 解析完成，共 {len(blocks)} 筆裝備。")
    return blocks


def resolve_name_conflicts(parsed_items, equipment_blocks):
    """
    parsed_items: parse_lub_file() 的結果
    equipment_blocks: parse_equipment_blocks() 的結果
    只對有能力區塊的 itemID 執行名稱重複處理
    """

    # 只取出「有能力」的物品
    affected_items = {
        item_id: parsed_items[item_id]
        for item_id in equipment_blocks.keys()
        if item_id in parsed_items
    }

    # 統計名稱出現次數
    name_count = {}
    for item_id, info in affected_items.items():
        name = info["name"]
        name_count[name] = name_count.get(name, 0) + 1

    # 只有重複名稱需要加 itemID
    for item_id, info in affected_items.items():
        name = info["name"]
        if name_count[name] > 1:
            #print(f"{name}")
            info["name"] = f"{name} (ID:{item_id})"

    # 注意：parsed_items 本身也會被更新（因為 dict 是參考）
    return parsed_items

def load_skill_map(filepath=None):
    global skill_map, skill_map_all, skill_df
    import skill_tree
    import pandas as pd
    import os

    # 若 filepath 沒指定 → 不做任何事
    if filepath is None:
        print("未指定路徑，使用預設空白技能列表。")
        return

    if not os.path.exists(filepath):
        print(f"{filepath} 找不到，保留空白技能列表。")
        return

    skill_df = pd.read_csv(filepath)

    # === ItemSearchApp 用 ===
    skill_map = dict(zip(skill_df["ID"], skill_df["Name"]))
    skill_map_all = skill_df.set_index("ID").to_dict(orient="index")

    # === skill_tree 用 ===
    skill_tree.skill_id_to_name = dict(zip(skill_df["ID"], skill_df["Name"]))
    skill_tree.skill_code_to_id = dict(zip(skill_df["Code"], skill_df["ID"]))
    skill_tree.skill_code_to_name = dict(zip(skill_df["Code"], skill_df["Name"]))


    print("技能列表載入成功")




def run_replay_and_dump():
    # 1. 選擇 RRF
    root = tk.Tk()
    root.withdraw()

    rrf_path = filedialog.askopenfilename(
        title="選擇 RRF 檔案",
        filetypes=[("Ragnarok Replay Files", "*.rrf"), ("All Files", "*.*")]
    )
    if not rrf_path:
        print("使用者取消選擇。")
        return None, None

    # 2. 指定 temp.txt 輸出位置
    output_txt = "tmp/temp.txt"

    # 3. 執行外部 exe 並將輸出寫入 temp.txt
    exe_path = "APP/RagnarokReplayExample.exe"  # 如果 exe 不在同資料夾請改成絕對路徑

    cmd = f'"{exe_path}" "{rrf_path}" > "{output_txt}"'

    print("執行中：", cmd)
    subprocess.run(cmd, shell=True)

    # 4. 回傳 temp.txt 路徑
    if os.path.exists(output_txt):
        print("解析完成，已產生：", output_txt)
        return rrf_path, output_txt

    print("錯誤：找不到 temp.txt")
    return rrf_path, None

#截取技能等級
import string

def is_valid_skill_name(s):
    # 技能名至少 6 個字元，全部由 A~Z、0~9、_ 組成，且必須包含 _
    if len(s) < 3:
        return False
    
    allowed = string.ascii_uppercase + string.digits + "_"
    
    for ch in s:
        if ch not in allowed:
            return False
    
    # 新增：一定要至少有一個 _
    if "_" not in s:
        return False
    
    return True



def parse_skillinfo_list_from_text(content):
    # 用 find 取最外層 {}
    start = content.find('{')
    end = content.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return []

    block = content[start+1:end]
    hex_list = re.findall(r'\b([0-9A-Fa-f]{2})\b', block)
    n = len(hex_list)

    skills = []
    i = 0

    while i < n - 20:

        # 前兩 byte 不為 00 → 初步可能是技能名
        if hex_list[i] != "00" and hex_list[i+1] != "00":

            name_start = i

            # 抓技能名直到 00
            name_bytes = []
            j = i
            while j < n and hex_list[j] != "00":
                name_bytes.append(hex_list[j])
                j += 1

            # 轉 ASCII
            try:
                name = bytes.fromhex("".join(name_bytes)).decode("ascii", errors="ignore")
            except:
                name = ""

            # ★★★ 加上這個：不是合法技能名 → 跳過
            if not is_valid_skill_name(name):
                i += 1
                continue

            # 取技能等級（前 6 bytes 的頭 2 bytes）
            lvl_pos = name_start - 6
            level = 0
            if lvl_pos >= 0:
                lv_low = int(hex_list[lvl_pos], 16)
                lv_high = int(hex_list[lvl_pos + 1], 16)
                level = lv_high * 256 + lv_low

            skills.append((name, level))

            i = j + 1
        else:
            i += 1

    return skills





def bytes_to_int_le(b):
    return int(''.join(reversed(b)), 16)

import re

def extract_session_stats(filepath):
    with open(filepath, 'r', encoding='cp950', errors='ignore') as f:
        content = f.read()

    target_fields = [
        "Job", "Level", "JobLevel",
        "Str", "Agi", "Vit", "Int", "Dex", "Luk"
    ]

    results = {}

    # --------------------------
    # 數值類 (4 bytes)
    # --------------------------
    for field in target_fields:
        pat = (
            r"\[Chunk Session\] Unparsed opcode " + field +
            r", Length=4\s+→ Raw hex:[^\{]*\{([^}]*)\}"
        )
        m = re.search(pat, content, re.DOTALL)
        if not m:
            continue

        block = m.group(1)

        data_bytes = []
        for line in block.splitlines():
            line = line.strip()
            hexes = re.findall(r'\b([0-9A-Fa-f]{2})\b', line)
            if len(hexes) >= 4:
                data_bytes.extend(hexes[-4:])  # 只抓最後 4 bytes

        if len(data_bytes) == 4:
            val = int(''.join(reversed(data_bytes)), 16)
            results[field] = val


    # --------------------------
    # HEADER_ZC_COUPLESTATUS：解析所有封包，取最後更新
    # --------------------------
    pat_couple = r"packet HEADER_ZC_COUPLESTATUS.*?\{([^}]*)\}"
    all_matches = re.findall(pat_couple, content, re.DOTALL)

    # 對照表
    attr_map = {
        0xdb: "POW",
        0xdc: "STA",
        0xdd: "WIS",
        0xde: "SPL",
        0xdf: "CON",
        0xe0: "CRT",
    }

    # 逐筆處理，後出現的會覆蓋前面的
    for block in all_matches:

        # 抓全部 hex bytes
        hex_list = re.findall(r'\b([0-9A-Fa-f]{2})\b', block)
        if len(hex_list) < 8:
            continue

        # 第 3 byte = 屬性 ID（index 2）
        attr_id = int(hex_list[2], 16)

        # 第 7+8 byte = 數值（little-endian）
        low = int(hex_list[6], 16)
        high = int(hex_list[7], 16)
        value = (high << 8) | low

        # 若 ID 有在對照表中 -> 記錄 (後面出現的會覆蓋)
        if attr_id in attr_map:
            results[attr_map[attr_id]] = value

    # --------------------------
    # 新增：Charactername (64 bytes，Big5)
    # --------------------------
    pat_name = (
        r"\[Chunk ReplayData\] Unparsed opcode Charactername, Length=64"
        r".*?Raw hex:[^\{]*\{([^}]*)\}"
    )
    m = re.search(pat_name, content, re.DOTALL)
    if m:
        block = m.group(1)
        hex_list = []

        for line in block.splitlines():
            line = line.strip()
            hexes = re.findall(r'\b([0-9A-Fa-f]{2})\b', line)
            # 每行最多取 16 bytes (正常 hex dump 格式)
            hex_list.extend(hexes)

        # 只取 64 bytes
        hex_list = hex_list[:64]

        # 轉成 bytes
        raw_bytes = bytes(int(h, 16) for h in hex_list)

        # 去除後面 NUL padding
        raw_bytes = raw_bytes.split(b'\x00', 1)[0]

        try:
            name = raw_bytes.decode('big5', errors='ignore')
        except:
            name = ""

        results["Charactername"] = name

    return results




def extract_equip_chunk(filepath, json_data, get_itemname, chunk_name="EquippedItems", group_map=None):

    with open(filepath, 'r', encoding='cp950', errors='ignore') as f:
        content = f.read()

    pattern = (
        r"\[Chunk Items\] Unparsed opcode " + re.escape(chunk_name) +
        r", Length=\d+\s+→ Raw hex:\s*\[[^\]]+\]\s*\{([\s\S]*?)^\}"
    )

    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(f"找不到指定chunk！({chunk_name})")
        return

    hex_body = match.group(1)
    hex_list = []
    for line in hex_body.splitlines():
        line = re.sub(r'^\s*[0-9A-Fa-f]{4,}\s+', '', line)
        hex_line = re.findall(r'([0-9A-Fa-f]{2})', line)
        if hex_line:
            hex_list.extend(hex_line)

    group_tag = '1901'
    n = len(hex_list)
    group_starts = []
    for i in range(n-1):
        if hex_list[i].lower() == group_tag[:2] and hex_list[i+1].lower() == group_tag[2:]:
            group_starts.append(i)
    group_starts.append(n)

    slot_tags = [
        '1901','1b01','1d01','1c01','1e01','1f01','2001','2101','2301','2701','2b01','2201','2401',
        '2501','2601','2801','2901','2a01','2c01','2d01','1a01'
    ]

    for g in range(len(group_starts)-1):
        group_number = g + 1
        if group_map is None:
            group_map = GROUP_NAME_MAP   # 預設仍使用原本那套

        group_name = group_map.get(group_number, f'未知部位{group_number}')
        if SHOW_GROUP_NAMES and group_name not in SHOW_GROUP_NAMES:
            continue
        if SHOW_GROUPS and group_number not in SHOW_GROUPS:
            continue

        group_start = group_starts[g]
        group_end = group_starts[g+1]
        group_bytes = hex_list[group_start:group_end]

        group_lines = []
        group_has_data = False

        slot_offsets = []
        for slot in slot_tags:
            slot1, slot2 = slot[:2], slot[2:]
            idx = None
            for i in range(len(group_bytes)-1):
                if group_bytes[i].lower() == slot1 and group_bytes[i+1].lower() == slot2:
                    idx = i
                    break
            slot_offsets.append(idx)

        for si, idx in enumerate(slot_offsets):
            slot_name = slot_tags[si].upper()
            # 只顯示有解析開關的slot
            should_parse = False
            if slot_name == '2201' and SHOW_2201:
                should_parse = True
            elif slot_name == '2301' and SHOW_2301:
                should_parse = True
            elif slot_name == '2701' and SHOW_2701:
                should_parse = True
            elif slot_name == '2D01' and SHOW_2D01:
                should_parse = True
            elif slot_name == '2B01' and SHOW_2B01:
                should_parse = True

            if SHOW_ONLY_PARSED_SLOTS and not should_parse:
                continue

            if idx is None:
                continue

            next_idx = None
            for ni in range(si+1, len(slot_offsets)):
                if slot_offsets[ni] is not None and slot_offsets[ni] > idx:
                    next_idx = slot_offsets[ni]
                    break
            slot_bytes = group_bytes[idx:next_idx] if next_idx else group_bytes[idx:]

            # 沒有資料(除了slot標頭以外沒內容)的也不顯示
            if SHOW_ONLY_FILLED and (len(slot_bytes) <= 4):
                continue

            # slot有資料才進來
            slot_content = []
            show_title = f'---- Slot {slot_name}'
            if SHOW_OFFSET:
                show_title += f' (offset={idx})'
            show_title += ' ----'
            slot_content.append(show_title)
            if SHOW_RAW:
                for j in range(0, len(slot_bytes), 8):
                    slot_content.append(' '.join(slot_bytes[j:j+8]))
            slot_json_name = group_name 
            # 特殊解析
            if slot_name == '2201':
                try:
                    card_ids = [
                        bytes_to_int_le(slot_bytes[6:9]),
                        bytes_to_int_le(slot_bytes[10:13]),
                        bytes_to_int_le(slot_bytes[14:17]),
                        bytes_to_int_le(slot_bytes[18:21]),
                    ]

                    slot_content.append(f'四洞卡片ID：')

                    for i, cid in enumerate(card_ids, 1):

                        # 若沒有資料 → JSON 要寫空白 ""
                        if cid == 0:
                            cname = ""
                            cid = ""
                        else:
                            cname = get_itemname(cid)

                        # 印出（如果 cname 空，就顯示卡{i}: 無）
                        show_name = cname if cname else ""
                        slot_content.append(f'  卡{i}: {cid}　{show_name}')

                        # JSON 欄位：「頭上_card1」「頭上_card2」
                        json_key = f"{group_name}_card{i}"
                        json_data[json_key] = str(cname)  # 確保 JSON 一律是字串

                except Exception:
                    slot_content.append('解析卡片ID失敗，檢查slot長度與資料')

            elif slot_name == '2301':
                try:
                    equip_id = bytes_to_int_le(slot_bytes[6:9])

                    if equip_id == 0:
                        equip_name = ""
                    else:
                        equip_name = get_itemname(equip_id)

                    slot_content.append(f'裝備名稱ID：{equip_id}　{equip_name if equip_name else "無"}')
                    json_data[f"{slot_json_name}_equip"] = str(equip_name)
                except:
                    slot_content.append('解析裝備名稱ID失敗，檢查slot長度與資料')

            elif slot_name == '2701':
                try:
                    refine_lv = int(slot_bytes[6], 16)
                    slot_content.append(f'精煉等級：{refine_lv}')
                    json_data[f"{slot_json_name}"] = str(refine_lv)
                except:
                                slot_content.append('解析精煉等級失敗，檢查slot長度與資料')
            elif slot_name == '2D01':
                try:
                    enchant_desc_list = []      # 顯示用（中文）
                    enchant_json_list = []      # JSON 用（AddExtParam / RaceAddDamage...）

                    for i in range(4):
                        id_idx = 6 + i * 5
                        val_idx = 8 + i * 5
                        if val_idx >= len(slot_bytes):
                            break

                        enchant_id = int(slot_bytes[id_idx], 16)
                        enchant_val = int(slot_bytes[val_idx], 16)

                        # 沒有附魔
                        if enchant_id == 0 and enchant_val == 0:
                            desc_text = ""
                            json_text = ""
                            show_text = "無"
                        else:
                            # ↙ 一次取得中文描述 & JSON 格式（你前面建好的 function）
                            desc_text, json_text = get_enchant_info(enchant_id, enchant_val)

                            show_text = desc_text
                            enchant_desc_list.append(desc_text)
                            enchant_json_list.append(json_text)

                        # 顯示
                        slot_content.append(f'  詞條{i+1}：{show_text}')

                    # ★★★ JSON：只有一個 note，把所有附魔用 \n 合併 ★★★
                    if enchant_json_list:
                        json_data[f"{slot_json_name}_note"] = "\n".join(enchant_json_list)
                    else:
                        json_data[f"{slot_json_name}_note"] = ""

                except Exception:
                    slot_content.append("解析2D01附魔資料失敗")

            elif slot_name == '2B01':
                try:
                    grade = int(slot_bytes[6], 16)
                    grade_name = GRADE_MAP.get(grade, str(grade))
                    slot_content.append(f'裝備階級：{grade_name}')
                    json_data[f"{slot_json_name}_階級"] = grade_name
                except:
                    slot_content.append('解析2B01裝備階級失敗，檢查slot長度與資料')

            group_lines.extend(slot_content)
            group_has_data = True

        # group有任何slot要顯示才印出
        if group_has_data:
            print(f'==== {chunk_name} Group {group_number}（{group_name}）====')
            for line in group_lines:
                print(line)
            print()


    print("Done.\n")

def run_rrf_main():
       # 0. 載入 iteminfo
    iteminfo_dict = parse_lub_file("data/iteminfo_new.lua")
    with open("data/EquipmentProperties.lua", "r", encoding="utf-8") as f:
        content = f.read()
    sequipment_data = parse_equipment_blocks(content)
    iteminfo_dict = resolve_name_conflicts(iteminfo_dict ,sequipment_data)#重複物品名稱加上id
    def get_itemname(item_id):
        info = iteminfo_dict.get(item_id)
        if info:
            return info["name"]
        return f"[{item_id}]"

    with open("data/default.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)

    # 1. 選 RRF → 執行 exe → 產出 temp.txt
    rrf_path, txt_path = run_replay_and_dump()
    if not txt_path:
        #input("按 Enter 結束...")
        exit()

    # 2. 解析技能資訊 
    with open(txt_path, "r", encoding="cp950", errors="ignore") as f:
        replay_text = f.read()

    skills = parse_skillinfo_list_from_text(replay_text)
    load_skill_map("data/skillneme.csv") 
    from skill_tree import skill_code_to_name, skill_code_to_id

    print("========== 技能清單 ==========")

    skill_json_list = []   # ★ 用來輸出 JSON 的 note

    for code, lv in skills:
        # 技能名稱：依前 23 字比對
        skill_prefix_map = {k[:23]: v for k, v in skill_code_to_name.items()}
        cname = skill_prefix_map.get(code[:23], code)

        # 技能 ID：也是依前 23 字比對 skill_code_to_id
        skill_prefix_id_map = {k[:23]: v for k, v in skill_code_to_id.items()}
        skill_id = skill_prefix_id_map.get(code[:23], 0)

        # 顯示用
        print(f"{cname:<23} 等級 {lv}")

        # ★ JSON 用 EnableSkill(技能ID, lv)
        if skill_id != 0:
            skill_json_list.append(f"EnableSkill({skill_id}, {lv})")

    print("")
    json_data["技能_note"] = "\n".join(skill_json_list)
    # 3.★ 解析角色 Session 資料
    session_data = extract_session_stats(txt_path)

    # 角色基本資料
    json_data["BaseLv"] = str(session_data.get("Level", ""))
    json_data["JobLv"] = str(session_data.get("JobLevel", ""))
    job_id = session_data.get("Job")
    job_info = job_dict.get(job_id)
    json_data["JOB"] = str(job_info["name"]) if job_info else ""

    for k in ["Str","Agi","Vit","Int","Dex","Luk","POW","STA","WIS","SPL","CON","CRT"]:
        if k in session_data:
            json_data[k.upper()] = str(session_data[k])

    print("========== 角色資訊 ==========")
    if "Charactername" in session_data:
        print(f"角色名稱：{session_data['Charactername']}")
    if "Job" in session_data:
        job_id = session_data["Job"]
        job_info = job_dict.get(job_id)

        if job_info:
            job_name = job_info.get("name", f"未知職業({job_id})")
            print(f"職業：{job_name}")
        else:
            print(f"職業：未知職業 (ID: {job_id})")
    if "Level" in session_data:
        print(f"角色等級：{session_data['Level']}")
    if "JobLevel" in session_data:
        print(f"Job 等級：{session_data['JobLevel']}")

    print("------ 基礎素質 ------")
    for stat in ["Str", "Agi", "Vit", "Int", "Dex", "Luk", "POW", "STA", "WIS", "SPL", "CON", "CRT"]:
        if stat in session_data:
            print(f"{stat}: {session_data[stat]}")
    print("")
    
    # 4. 用 temp.txt 開始解析
    extract_equip_chunk(txt_path, json_data, get_itemname,'EquippedItems', GROUP_NAME_MAP)
    extract_equip_chunk(txt_path, json_data, get_itemname,'EquippedShadowItems', Shadow_GROUP_NAME_MAP)


    # 5. 解析完畢 → 刪除 temp.txt
    try:
        if os.path.exists(txt_path):
            os.remove(txt_path)
            print(f"已刪除暫存檔：{txt_path}")
    except Exception as e:
        print(f"刪除 {txt_path} 時發生錯誤：{e}")

    # 依照輸入的 RRF 自動命名 json
    rrf_filename = os.path.basename(rrf_path)        # 例：abc.rrf
    json_name = os.path.splitext(rrf_filename)[0] + ".json"
    json_output_path = os.path.join("tmp", json_name)

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    # === 告訴 GUI 輸出的 json 是哪個 ===
    with open("tmp/rrf_output_path.txt", "w", encoding="utf-8") as f:
        f.write(json_output_path)

    print(f"JSON 已輸出為 {json_output_path}")
    #input("按 Enter 結束...")

    return json_output_path

if __name__ == "__main__":
    run_rrf_main()