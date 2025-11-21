<<<<<<< HEAD
import sys
=======
﻿import sys
>>>>>>> 4c231af3473bdd98b7c9507febca4a266db18240
import os
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QTableWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTableWidgetItem, QLabel, QTabWidget , QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView
from PySide6.QtWidgets import QToolTip
from PySide6.QtGui import QCursor
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import QPoint
# ---------------------------------------------------------------
# 讀檔：自動嘗試多種編碼
# ---------------------------------------------------------------
def read_text_with_fallback(path):
    encodings = ["utf-8", "utf-8-sig", "cp950", "big5", "cp936", "cp932", "latin1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                data = f.read()
            print(f"[INFO] 使用 {enc} 讀取成功：{path}")
            return data
        except Exception:
            continue

    with open(path, "rb") as f:
        data = f.read().decode("latin1", errors="replace")
    print(f"[WARN] 所有編碼失敗，改用 latin1+replace：{path}")
    return data


# ---------------------------------------------------------------
# 解析 iteminfo_new.lua   => {item_id: {"name": 顯示名, "kr_name": 資源名}}
# ---------------------------------------------------------------
def parse_lub_file(filename):#字典化物品列表


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
    total = len(item_entries)
    print(f"📦 開始讀取 {os.path.basename(filename)}，共 {total} 筆物品資料。")
    
    
    
    #for item_id, body in item_entries:
    for index, (item_id, body) in enumerate(item_entries, start=1):
        
        try:
            
            print(f"  → 正在讀取第 {index}/{total} 筆", end="\r")
            item_id = int(item_id)
            identified_name = re.search(r'(?<!un)identifiedDisplayName\s*=\s*"([^"]+)"', body)

            kr_name = re.search(r'(?<!un)identifiedResourceName\s*=\s*"([^"]+)"', body)
            slot = re.search(r'slotCount\s*=\s*(\d+)', body)

            desc_match = re.search(r'(?<!un)identifiedDescriptionName\s*=\s*{(.*?)}', body, re.DOTALL)
            if desc_match:
                desc_body = desc_match.group(1)
                desc_lines_raw = re.findall(r'"([^"]*)"', desc_body)
                desc_lines = []
                for line in desc_lines_raw:
                    cleaned = line.strip()
                    # 控制碼行過濾，但保留真正空白行
                    if re.fullmatch(r"\^?[a-fA-F0-9]+", cleaned):
                        continue
                    elif cleaned == "":
                        desc_lines.append("")  # 保留空白行
                    else:
                        desc_lines.append(cleaned)


            else:
                desc_lines = []
            
            if identified_name and kr_name and slot:
                base_name = identified_name.group(1).strip()
                slot_count = int(slot.group(1))

                # ✅ 名稱加上孔數
                if slot_count > 0:
                    display_name = f"{base_name} [{slot_count}]"
                else:
                    display_name = base_name

                parsed_items[item_id] = {
                    "name": display_name,           # 已經含孔數
                    "base_name": base_name,         # 如果以後要用純名稱，可以保留
                    "kr_name": kr_name.group(1).strip(),
                    "description": desc_lines,
                    "slot": slot_count
                }

        except Exception:
            continue
    print(f"\n✅ 讀取完成，共成功解析 {len(parsed_items)} 筆。")
    return parsed_items


# ---------------------------------------------------------------
# 解析 ItemDBNameTbl.lua  => {"DBName": item_id}
# ---------------------------------------------------------------
def parse_itemdb_name_tbl(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 找不到檔案：{filename}")
        return {}
    except UnicodeDecodeError:
        with open(filename, "rb") as f:
            content = f.read().decode("latin1", errors="replace")

    # 支援  Name = 123  或  ["Name"] = 123
    pattern = r'(?:\["([^"]+)"\]|([A-Za-z0-9_]+))\s*=\s*(\d+)'
    name_to_id = {}

    for m in re.finditer(pattern, content):
        key1, key2, val = m.groups()
        key = key1 or key2
        if key:
            name_to_id[key] = int(val)

    print(f"[INFO] ItemDBNameTbl 解析完成，共 {len(name_to_id)} 筆")
    return name_to_id


# ---------------------------------------------------------------
# 解析 EnchantList.lua
# parsed 結構：
#   { table_id: {
#       "slot_order": [3,2,1],
#       "target_items": ["N_Avenger_Cape_TW", ...],
#       "slots": {
#          slot_id: {
#             "enchants": [(grade, name, rate), ...],
#             "perfect":  [{"name": n, "rate": r, "materials": [...]}, ...]
#          }
#       }
#   } }
# ---------------------------------------------------------------
def parse_enchant_list(filename):
    if not os.path.exists(filename):
        print("❌ 找不到檔案", filename)
        return {}

    content = read_text_with_fallback(filename)

    # 找出所有 CreateEnchantInfo
    tables = re.split(r"Table\[(\d+)\]\s*=\s*CreateEnchantInfo\(\s*\)", content)
    if len(tables) <= 1:
        print("⚠ 解析不到任何 Table")
        return {}

    parsed = {}

    # 先逐 Table 把 slot_order / target_items / reset 抓出來
    for i in range(1, len(tables), 2):
        tid = int(tables[i])
        body = tables[i + 1]

        parsed[tid] = {
            "slot_order": [],
            "target_items": [],
            "reset": None,
            "slots": {}
        }

        # SetSlotOrder(3, 2, 1)
        sso = re.search(r"SetSlotOrder\((.*?)\)", body)
        if sso:
            nums = [
                int(x.strip()) for x in sso.group(1).split(",")
                if x.strip().isdigit()
            ]
            parsed[tid]["slot_order"] = nums

        # AddTargetItem("xxx")
        targets = re.findall(r'AddTargetItem(?:_Duplicate)?\("([^"]+)"\)', body)
        parsed[tid]["target_items"] = targets

        # SetReset(true, 80000, 0, {"Silvervine", 3})
        rst = re.search(
            r"SetReset\((true|false)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*((?:\{.*?\})+))?",
            body,
            re.DOTALL
        )
        if rst:
            enable = rst.group(1) == "true"
            rr = int(rst.group(2))
            er = int(rst.group(3))

            mats = []
            raw = rst.group(4)
            if raw:
                mats = [
                    (a, int(b))
                    for a, b in re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', raw)
                ]
            parsed[tid]["reset"] = {
                "enable": enable,
                "reset_rate": rr,
                "enchant_rate": er,
                "materials": mats,
            }

    # --------------------------------------------------
    # 解析 SetRequire (支援多材料)
    # --------------------------------------------------
    all_requires = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetRequire'
        r'\(\s*(\d+)\s*,\s*((?:\{[^}]+\}\s*,?\s*)+)\)',
        content
    )

    for tid, sid, zeny, mats_raw in all_requires:
        tid = int(tid)
        sid = int(sid)

        if tid not in parsed:
            continue

        parsed[tid]["slots"].setdefault(sid, {
            "enchants": [],
            "perfect": [],
            "upgrade": [],
            "perfect_upgrade": [],
            "random_upgrade": []
        })

        # 找出多組 {"Name", 1}
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["require"] = {
            "zeny": int(zeny),
            "materials": materials
        }



    # --------------------------------------------------
    # 全檔掃描 SetEnchant
    # --------------------------------------------------
    all_enchants = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetEnchant\(\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\)',
        content
    )

    for tid, sid, grade, name, rate in all_enchants:
        tid = int(tid)
        sid = int(sid)
        grade = int(grade)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": []
            }

        parsed[tid]["slots"][sid]["enchants"].append((grade, name, rate))

    # --------------------------------------------------
    # 全檔掃描 AddPerfectEnchant
    # --------------------------------------------------
    all_perfects = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddPerfectEnchant'
        r'\(\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, name, rate, mats_raw in all_perfects:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": []
            }

        mats = re.findall(r'\{\s*"([^"]*)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["perfect"].append({
            "name": name,
            "rate": rate,
            "materials": materials
        })

    # --------------------------------------------------
    # 全檔掃描 AddUpgradeEnchant
    # --------------------------------------------------
    all_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, src, dst, rate, mats_raw in all_upgrades:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("upgrade", [])

        # 解析材料
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["upgrade"].append({
            "from": src,
            "to": dst,
            "rate": rate,
            "materials": materials
        })

    # --------------------------------------------------
    # 完美升階 AddPerfectUpgradeEnchant
    # --------------------------------------------------
    all_perfect_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddPerfectUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{.*?\})+)\)',
        content,
        re.DOTALL
    )

    for tid, sid, src, dst, rate, mats_raw in all_perfect_upgrades:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": [],
                "perfect_upgrade": [],
                "random_upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("perfect_upgrade", [])

        # 材料
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid]["perfect_upgrade"].append({
            "from": src,
            "to": dst,
            "rate": rate,
            "materials": materials
        })
    # --------------------------------------------------
    # 解析 SetRandomUpgradeRequire
    # --------------------------------------------------
    all_random_require = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:SetRandomUpgradeRequire'
        r'\(\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*((?:\{[^}]+\}\s*,?\s*)+)\)',
        content
    )

    for tid, sid, src, rate, mats_raw in all_random_require:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        parsed[tid]["slots"].setdefault(sid, {
            "enchants": [],
            "perfect": [],
            "upgrade": [],
            "perfect_upgrade": [],
            "random_upgrade": []
        })

        # 多組材料解析
        mats = re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', mats_raw)
        materials = [(m_name, int(m_cnt)) for m_name, m_cnt in mats]

        parsed[tid]["slots"][sid].setdefault("random_require", {})

        parsed[tid]["slots"][sid]["random_require"][src] = {
            "rate": rate,
            "materials": materials
        }
    # --------------------------------------------------
    # 機率升階 AddRandomUpgradeEnchant
    # --------------------------------------------------
    all_random_upgrades = re.findall(
        r'Table\[(\d+)\]\.Slot\[(\d+)\]\:AddRandomUpgradeEnchant'
        r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\)',
        content
    )

    for tid, sid, src, dst, rate in all_random_upgrades:
        tid = int(tid)
        sid = int(sid)
        rate = int(rate)

        if tid not in parsed:
            continue

        if sid not in parsed[tid]["slots"]:
            parsed[tid]["slots"][sid] = {
                "enchants": [],
                "perfect": [],
                "upgrade": [],
                "perfect_upgrade": [],
                "random_upgrade": []
            }
        else:
            parsed[tid]["slots"][sid].setdefault("random_upgrade", [])

        parsed[tid]["slots"][sid]["random_upgrade"].append({
            "from": src,
            "to": dst,
            "rate": rate,
            "materials": parsed[tid]["slots"][sid]
                .get("random_require", {})
                .get(src, {})
                .get("materials", [])
        })






    print(f"✅ 完成解析，共 {len(parsed)} 組 Table")
    return parsed


# ============================================================
# PySide6 UI
# ============================================================
from PySide6.QtWidgets import (
    QWidget, QListWidget, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QTabWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt


class EnchantUI(QWidget):
    def __init__(self, enchant_data, item_data, itemdb):
        super().__init__()

        self.parsed = enchant_data        # EnchantList 解析結果
        self.items = item_data           # iteminfo_new
        self.itemdb = itemdb             # ItemDBNameTbl

        self.setWindowTitle("Enchant Viewer")
        layout = QHBoxLayout(self)

        # ==============================
        # 左區域（搜尋欄 + 裝備列表）
        # ==============================
        left_box = QVBoxLayout()
        layout.addLayout(left_box)

        # ▶ 搜尋欄
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋裝備名稱...")
        left_box.addWidget(self.search_box)

        # ▶ 裝備列表
        self.list_items = QListWidget()
        left_box.addWidget(self.list_items)

        # ==============================
        # 右：附魔資訊（Tab）
        # ==============================
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # -----------------------------------------------------------
        # 建立：裝備名稱 → 所屬 Enchant Table 映射
        # -----------------------------------------------------------
        self.all_target_items = {}  # key: 顯示名, value: table_id

        for tid, data in self.parsed.items():
            for raw_name in data["target_items"]:
                disp = self.resolve_item_name(raw_name)
                self.all_target_items[disp] = tid

        # 顯示所有裝備
        #self.full_item_list = sorted(self.all_target_items.keys())
        self.full_item_list = sorted(
        self.all_target_items.keys(),
        key=lambda name: (self.all_target_items[name], name)
    )
        self.refresh_item_list("")
        self.adjust_left_list_width()

        # 綁定搜尋事件
        self.search_box.textChanged.connect(self.refresh_item_list)

        # 點選裝備
        self.list_items.currentTextChanged.connect(self.select_equipment)



    # def show_materials(self, row, col):
    #     tab_index = self.tabs.currentIndex()
    #     tab_widget = self.tabs.widget(tab_index)

    #     table = tab_widget.findChild(QTableWidget)
    #     if not table:
    #         return

    #     item = table.item(row, 1)
    #     if not item:
    #         return

    #     data = item.data(Qt.UserRole)
    #     if not data:
    #         return

    #     mlist = []

    #     # 取得 slot info
    #     equip_name = self.list_items.currentItem().text()
    #     tid = self.all_target_items[equip_name]
    #     info = self.parsed[tid]

    #     slot_order = list(reversed(info["slot_order"]))
    #     sid = slot_order[tab_index]
    #     slot_info = info["slots"].get(sid)

    #     # -------------------------------------------------------
    #     # ① 只有一般附魔(enchant) 才讀取 SetRequire 材料
    #     # -------------------------------------------------------
    #     if data["type"] == "enchant":
    #         if slot_info and "require" in slot_info:
    #             for name, cnt in slot_info["require"]["materials"]:
    #                 mlist.append((self.resolve_item_name(name), cnt))

    #     # -------------------------------------------------------
    #     # ② 個別附魔（perfect / upgrade / perfect_upgrade / random_upgrade）
    #     # -------------------------------------------------------
    #     if data["type"] in ("perfect", "upgrade", "perfect_upgrade"):
    #         for name, cnt in data["materials"]:
    #             mlist.append((self.resolve_item_name(name), cnt))

    #     # 機率升階一般沒有材料
    #     # if data["type"] == "random_upgrade": pass
    #     elif data["type"] == "random_upgrade":
    #         mats = data.get("materials", [])
    #         for name, cnt in mats:
    #             mlist.append((self.resolve_item_name(name), cnt))

    #     # -------------------------------------------------------
    #     # 顯示
    #     # -------------------------------------------------------
    #     if not mlist:
    #         QMessageBox.information(self, "材料", "此附魔不需要額外材料。")
    #         return

    #     msg = ""
    #     for name, cnt in mlist:
    #         msg += f"● {name} × {cnt}\n"

    #     QMessageBox.information(self, "材料", msg)



    def show_materials(self, row, col):
        tab_index = self.tabs.currentIndex()
        tab_widget = self.tabs.widget(tab_index)

        table = tab_widget.findChild(QTableWidget)
        if not table:
            return

        item = table.item(row, 1)
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        # ---------------------------------------------------------
        # ① 顯示標題：附魔名稱（升階附魔要顯示 from → to）
        # ---------------------------------------------------------
        title = ""
        rate_text = ""
        if "rate" in data:
            value = data["rate"] / 1000
            text = f"{value:.3f}".rstrip('0').rstrip('.')
            rate_text = f"（機率 {text}%）"
        elif data["type"] in ("perfect", "upgrade", "perfect_upgrade"):
            rate_text = "（機率 100%）"


        # 各類型標題
        if data["type"] == "enchant":
            title = f"【機率附魔】{item.text()}{rate_text}"

        elif data["type"] == "perfect":
            title = f"【指定附魔】{item.text()}{rate_text}"

        elif data["type"] in ("upgrade", "perfect_upgrade"):
            src = self.resolve_item_name(data["from"])
            dst = self.resolve_item_name(data["to"])
            title = f"【指定升階】{src} → {dst}{rate_text}"

        elif data["type"] == "random_upgrade":
            src = self.resolve_item_name(data["from"])
            dst = self.resolve_item_name(data["to"])
            title = f"【機率升階】{src} → {dst}{rate_text}"

        else:
            title = item.text()

        # ---------------------------------------------------------
        # ② 收集材料
        # ---------------------------------------------------------
        mlist = []

        # 取得 slot info
        equip_name = self.list_items.currentItem().text()
        tid = self.all_target_items[equip_name]
        info = self.parsed[tid]
        slot_order = list(reversed(info["slot_order"]))
        sid = slot_order[tab_index]
        slot_info = info["slots"].get(sid)

        # SetRequire → 只有一般附魔需要
        if data["type"] == "enchant":
            if slot_info and "require" in slot_info:
                for name, cnt in slot_info["require"]["materials"]:
                    mlist.append((self.resolve_item_name(name), cnt))

        # 單項材料
        mats = data.get("materials", [])
        for name, cnt in mats:
            mlist.append((self.resolve_item_name(name), cnt))

        # 去掉空的 + 重複的
        cleaned = []
        seen = set()
        for name, cnt in mlist:
            if not name:
                continue
            key = (name, cnt)
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(key)
        mlist = cleaned

        # ---------------------------------------------------------
        # ③ 組 tooltip 文字
        # ---------------------------------------------------------
        msg = title + "\n"

        if not mlist:
            msg += "\n此附魔不需要額外材料。"
        else:
            msg += "\n"
            for name, cnt in mlist:
                msg += f"● {name} × {cnt}\n"

        msg = msg.rstrip()

        # ---------------------------------------------------------
        # ④ Tooltip 出現在滑鼠左上角（偏移避免被遮住）
        # ---------------------------------------------------------
        pos = QCursor.pos() + QPoint(10, -10)
        QToolTip.showText(pos, msg, table)


    def adjust_left_list_width(self):
        fm = QFontMetrics(self.list_items.font())
        max_width = 0

        for name in self.full_item_list:
            w = fm.horizontalAdvance(name)
            if w > max_width:
                max_width = w

        # 加上捲軸、邊框的空間（大約）
        max_width += 40

        self.list_items.setMinimumWidth(max_width)
        self.list_items.setMaximumWidth(max_width)
        self.search_box.setMinimumWidth(max_width)
        self.search_box.setMaximumWidth(max_width)
        

    # ==============================
    # 裝備名稱解析（DBName -> id -> 顯示名）
    # ==============================
    def resolve_item_name(self, key: str) -> str:
        display = key

        # ① DBName → item_id → 中文名
        item_id = self.itemdb.get(key)
        if item_id is not None:
            item_info = self.items.get(item_id)
            if item_info:
                return item_info["name"]

        # ② kr_name
        for info in self.items.values():
            if info["kr_name"] == key:
                return info["name"]

        return display

    # ==============================
    # 搜尋 + 重新填入列表
    # ==============================
    def refresh_item_list(self, text):
        text = text.strip().lower()
        self.list_items.clear()

        for name in self.full_item_list:
            if text in name.lower():  # 部分比對
                self.list_items.addItem(name)

    # ==============================
    # 選擇裝備
    # ==============================
    def select_equipment(self, equip_name: str):
        if not equip_name:
            return

        tid = self.all_target_items.get(equip_name)
        if tid is None:
            return

        self.load_all_slots_tabs(tid)

    # ==============================
    # 顯示該 table 所有 Slots 附魔
    # ==============================
    def load_all_slots_tabs(self, tid):
        self.tabs.clear()

        info = self.parsed.get(tid)
        if not info:
            return

        slot_name_map = {
            0: "第一洞",
            1: "第二洞",
            2: "第三洞",
            3: "第四洞",
        }

        for sid in reversed(info["slot_order"]):
            tab = QWidget()
            v = QVBoxLayout(tab)

            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Grade", "Enchant", "機率 (%)"])
            table.verticalHeader().setVisible(False)
            table.cellClicked.connect(self.show_materials)


            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.resizeSection(0, 80)
            header.resizeSection(2, 80)
            header.setSectionResizeMode(1, QHeaderView.Stretch)

            v.addWidget(table)

            title = slot_name_map.get(sid, f"第{sid}洞")
            self.tabs.addTab(tab, title)

            slot_info = info.get("slots", {}).get(sid)
            if not slot_info:
                continue

            enchants = slot_info.get("enchants", [])
            perfects = slot_info.get("perfect", [])
            upgrades = slot_info.get("upgrade", [])
            perfect_upgrades = slot_info.get("perfect_upgrade", [])
            random_upgrades = slot_info.get("random_upgrade", [])

            total_rows = (
                len(enchants) +
                len(perfects) +
                len(upgrades) +
                len(perfect_upgrades) +
                len(random_upgrades)
            )
            table.setRowCount(total_rows)

            row = 0

            # --------------------------------------------------
            # 合併一般附魔：只看名稱 + 機率，不看 Grade
            # --------------------------------------------------
            merged = {}  # key = (name, rate) → value = True

            for grade, name, rate in enchants:
            #     key = (name, rate)
            #     merged[key] = True  # 重複會自動覆蓋

            # # 寫入表格
            # for (name, rate) in merged.keys():
                table.setItem(row, 0, QTableWidgetItem("機率附魔"))  # 統一名稱
                item = QTableWidgetItem(self.resolve_item_name(name))
                item.setData(Qt.UserRole, {
                    "type": "enchant",
                    "name": name,
                    "rate": rate 
                })
                table.setItem(row, 1, item)
                table.setItem(row, 2, QTableWidgetItem(f"{rate/1000:.3f}"))
                value = rate / 1000
                text = f"{value:.3f}".rstrip('0').rstrip('.')
                table.setItem(row, 2, QTableWidgetItem(f"{text}%"))
                row += 1


            # 完美附魔
            for p in perfects:
                table.setItem(row, 0, QTableWidgetItem("指定附魔"))
                item = QTableWidgetItem(self.resolve_item_name(p["name"]))
                item.setData(Qt.UserRole, {
                    "type": "perfect",
                    "name": p["name"],
                    "materials": p["materials"],
                })
                table.setItem(row, 1, item)

                table.setItem(row, 2, QTableWidgetItem("100%"))
                row += 1

            # 升階 目前沒有物品會附魔失敗，都先寫100%
            for up in upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(row, 0, QTableWidgetItem("指定升階"))
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "materials": up["materials"],
                })
                table.setItem(row, 1, item)

                table.setItem(row, 2, QTableWidgetItem("100%"))#(f"{up['rate']/1000:.3f}"))

                row += 1

            # 完美升階
            for up in perfect_upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(row, 0, QTableWidgetItem("指定升階"))
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "perfect_upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "materials": up["materials"],
                })
                table.setItem(row, 1, item)

                table.setItem(row, 2, QTableWidgetItem("100%"))
                row += 1

            # 機率升階
            for up in random_upgrades:
                src = self.resolve_item_name(up["from"])
                dst = self.resolve_item_name(up["to"])
                table.setItem(row, 0, QTableWidgetItem("機率升階"))
                item = QTableWidgetItem(f"{src} → {dst}")
                item.setData(Qt.UserRole, {
                    "type": "random_upgrade",
                    "from": up["from"],
                    "to": up["to"],
                    "rate": up["rate"],
                    "materials": up.get("materials", [])
                })
                table.setItem(row, 1, item)

                #table.setItem(row, 2, QTableWidgetItem(f"{up['rate']/1000:.3f}"))
                value = up['rate'] / 1000
                text = f"{value:.3f}".rstrip('0').rstrip('.')
                table.setItem(row, 2, QTableWidgetItem(f"{text}%"))
                row += 1



# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
def main():
    app = QApplication(sys.argv)

    # base_dir = os.path.dirname(os.path.abspath(__file__))
    # item_path = os.path.join(base_dir, "data", "iteminfo_new.lua")
    # enchant_path = os.path.join(base_dir, "data", "EnchantList.lua")
    # itemdb_path = os.path.join(base_dir, "data", "ItemDBNameTbl.lua")

    # iteminfo = parse_lub_file(item_path)
    # enchant = parse_enchant_list(enchant_path)
    # itemdb = parse_itemdb_name_tbl(itemdb_path)

    # ui = EnchantUI(enchant, iteminfo, itemdb)
    # ui.resize(900, 600)
    # ui.show()
    # sys.exit(app.exec())


if __name__ == "__main__":
    main()
