import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QLineEdit, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


# ------------------------------------------------------------
# 自動編碼讀取
# ------------------------------------------------------------
def read_text_with_fallback(path):
    encodings = ["utf-8", "utf-8-sig", "cp950", "big5", "latin1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except:
            continue
    return open(path, "r", errors="replace").read()


# ------------------------------------------------------------
# 解析 iteminfo_new.lua
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# 解析 ItemDBNameTbl.lua
# ------------------------------------------------------------
def parse_itemdb_name_tbl(filename):
    content = read_text_with_fallback(filename)

    pattern = r'(?:\["([^"]+)"\]|([A-Za-z0-9_]+))\s*=\s*(\d+)'
    mapping = {}
    for m in re.finditer(pattern, content):
        key = m.group(1) or m.group(2)
        val = int(m.group(3))
        mapping[key] = val

    print(f"✔ ItemDBNameTbl 解析成功：{len(mapping)} 筆")
    return mapping


# ------------------------------------------------------------
# 解析 ReformInfo
# ------------------------------------------------------------
def parse_reform_info(filename):
    text = read_text_with_fallback(filename)

    # 找到 ReformInfo 大區塊
    m = re.search(r"ReformInfo\s*=\s*{(.*)}\s*$", text, re.DOTALL)
    if not m:
        print("❌ ReformInfo not found")
        return {}
    body = m.group(1)

    reform = {}

    # 尋找所有 [123] =
    for entry in re.finditer(r"\[(\d+)\]\s*=\s*{", body):
        rid = int(entry.group(1))
        start = entry.end()  # 從 { 後開始
        brace = 1
        i = start

        # 🔥 精準抓取整個 {...} 包含巢狀大括號
        while i < len(body) and brace > 0:
            if body[i] == '{':
                brace += 1
            elif body[i] == '}':
                brace -= 1
            i += 1

        block = body[start:i-1]

        # 解析內容
        def grab_str(key):
            m2 = re.search(rf'{key}\s*=\s*"([^"]*)"', block)
            return m2.group(1) if m2 else ""

        def grab_num(key):
            m2 = re.search(rf'{key}\s*=\s*(-?\d+)', block)
            return int(m2.group(1)) if m2 else 0

        def grab_bool(key):
            m2 = re.search(rf'{key}\s*=\s*(true|false)', block)
            return (m2.group(1) == "true") if m2 else False

        # 材料
        materials = []
        mat_m = re.search(r"Material\s*=\s*{(.*?)}", block, re.DOTALL)
        if mat_m:
            for m3 in re.finditer(r"([A-Za-z0-9_]+)\s*=\s*(\d+)", mat_m.group(1)):
                materials.append({"name": m3.group(1), "count": int(m3.group(2))})

        # 說明文字
        info_m = re.search(r"InformationString\s*=\s*{(.*?)}", block, re.DOTALL)
        info_list = re.findall(r'"([^"]*)"', info_m.group(1)) if info_m else []

        # 存入 ReformInfo table
        reform[rid] = {
            "BaseItem": grab_str("BaseItem"),
            "ResultItem": grab_str("ResultItem"),
            "Material": materials,
            "NeedRefineMin": grab_num("NeedRefineMin"),
            "NeedRefineMax": grab_num("NeedRefineMax"),
            "NeedOptionNumMin": grab_num("NeedOptionNumMin"),
            "IsEmptySocket": grab_bool("IsEmptySocket"),
            "ChangeRefineValue": grab_num("ChangeRefineValue"),
            "PreserveSocketItem": grab_bool("PreserveSocketItem"),
            "PreserveGrade": grab_bool("PreserveGrade"),
            "InformationString": info_list
        }

    print(f"✔ ReformInfo 正確解析：{len(reform)} 筆")
    return reform

# ------------------------------------------------------------
# 解析 ReformItemList
# ------------------------------------------------------------
def parse_reform_item_list(filename):
    text = read_text_with_fallback(filename)

    m = re.search(r"ReformItemList\s*=\s*{(.*?)}\s*$", text, re.DOTALL)
    if not m:
        print("❌ ReformItemList not found")
        return {}

    body = m.group(1)
    result = {}

    # key = C_Armor_Reform_1
    # value = {103, 105, 107}
    entries = re.findall(r"([A-Za-z0-9_]+)\s*=\s*{(.*?)}\s*,?", body, re.DOTALL)

    for key, inside in entries:
        ids = re.findall(r"(\d+)", inside)
        reform_ids = [int(x) for x in ids]
        result[key] = reform_ids

    print(f"✔ ReformItemList 解析完成，共 {len(result)} 組")
    return result

import re

def ro_color_to_html(s):
    """
    將 RO 顏色碼 ^RRGGBB內容^000000
    轉成 HTML span 樣式
    """
    # 找所有顏色碼片段
    def repl(match):
        color = match.group(1)
        text = match.group(2)
        return f'<span style="color:#{color}">{text}</span>'

    # 處理 ^RRGGBB內容^000000
    s = re.sub(r"\^([0-9A-Fa-f]{6})(.*?)\^000000", repl, s)

    return s

# ============================================================
# Reform UI
# ============================================================
from PySide6.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QLineEdit, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


class ReformUI(QWidget):
    def __init__(self, reform_data, item_data, itemdb, reform_item_list):
        super().__init__()

        self.reform = reform_data      # ReformInfo 的 dict
        self.items = item_data         # iteminfo_new.lua 解析結果：itemid -> {...}
        self.itemdb = itemdb           # ItemDBNameTbl：DBName -> itemid
        self.reform_item_list = reform_item_list

        self.setWindowTitle("改造系統檢視器 Reform Viewer")
        layout = QHBoxLayout(self)

        # --------------------------------------------------------
        # 左側：搜尋 + BaseItem 清單
        # --------------------------------------------------------
        left_box = QVBoxLayout()
        layout.addLayout(left_box)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋 要改造的裝備名稱...")
        left_box.addWidget(self.search_box)

        self.list_items = QListWidget()
        left_box.addWidget(self.list_items)

        # BaseItem(DBName) → ReformID list
        self.base_to_ids = {}
        for rid, info in self.reform.items():
            key = info["BaseItem"]
            self.base_to_ids.setdefault(key, []).append(rid)

        # 先把每個 BaseItem 轉成顯示名稱
        # self.full_list = []  # [(display_name, base_dbname), ...]
        # for base_key in sorted(self.base_to_ids.keys()):
        #     disp = self.resolve_item_name(base_key)
        #     self.full_list.append((disp, base_key))

        # 依 ReformInfo 出現順序建立 BaseItem 清單
        self.full_list = []
        seen = set()

        for rid, info in self.reform.items():    # reform 是有順序的 dict
            base_key = info["BaseItem"]

            if base_key not in seen:
                seen.add(base_key)
                disp = self.resolve_item_name(base_key)
                self.full_list.append((disp, base_key))


        # 填入清單
        self.refresh_item_list("")
        self.adjust_left_width()

        self.search_box.textChanged.connect(self.on_search_text_changed)
        self.list_items.currentRowChanged.connect(self.on_current_row_changed)

        # --------------------------------------------------------
        # 右側：每個 BaseItem 對應的 ReformID Tab
        # --------------------------------------------------------
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

    # --------------------------------------------------------
    # 重要：所有物品名稱都走 DBName -> itemid -> iteminfo_new
    # --------------------------------------------------------
    def resolve_item_name(self, dbname):
        """
        ReformInfo 裡的 BaseItem / ResultItem / Material 全部是 DBName。
        這裡一定要先用 ItemDBNameTbl 找 itemid，再用 iteminfo_new 找顯示名稱。
        """
        item_id = self.itemdb.get(dbname)
        if not item_id:
            return f"[未知DBName]{dbname}"

        info = self.items.get(item_id)
        if not info:
            return f"[未知ID]{item_id}"

        return info["name"]

    # --------------------------------------------------------
    def on_search_text_changed(self, text):
        self.refresh_item_list(text)

    def refresh_item_list(self, text):
        text = (text or "").lower().strip()
        self.list_items.clear()

        for disp, base_key in self.full_list:
            if text and text not in disp.lower():
                continue
            item = QListWidgetItem(disp)
            # 把「真正的 BaseItem DBName」塞進去，之後靠這個找資料
            item.setData(Qt.UserRole, base_key)
            self.list_items.addItem(item)

    # --------------------------------------------------------
    def adjust_left_width(self):
        if not self.full_list:
            return
        fm = QFontMetrics(self.list_items.font())
        width = max(fm.horizontalAdvance(d) for d, _ in self.full_list) + 40
        self.list_items.setMinimumWidth(width)
        self.list_items.setMaximumWidth(width)
        self.search_box.setMinimumWidth(width)
        self.search_box.setMaximumWidth(width)

    # --------------------------------------------------------
    def on_current_row_changed(self, row):
        if row < 0:
            return
        item = self.list_items.item(row)
        if not item:
            return
        base_key = item.data(Qt.UserRole)
        if not base_key:
            return

        rid_list = self.base_to_ids.get(base_key, [])
        self.load_tabs(rid_list)

    # --------------------------------------------------------
    def load_tabs(self, rid_list):
        self.tabs.clear()

        for rid in rid_list:
            info = self.reform[rid]

            tab = QWidget()
            v = QVBoxLayout(tab)

            # 標題：ResultItem
            lbl = QLabel(f"改造成 ➜ {self.resolve_item_name(info['ResultItem'])}")
            lbl.setStyleSheet("font-size:16px; font-weight:bold;")
            v.addWidget(lbl)

            # 條件表
            table = QTableWidget()
            table.setColumnCount(2)
            table.setRowCount(2)
            table.setHorizontalHeaderLabels(["條件", "內容"])
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            fixed_height = table.horizontalHeader().height() + table.rowCount() * 28
            table.setFixedHeight(fixed_height)

            v.addWidget(table)

            table.setItem(0, 0, QTableWidgetItem("精煉範圍"))
            table.setItem(0, 1, QTableWidgetItem(f"{info['NeedRefineMin']} ~ {info['NeedRefineMax']}"))

            table.setItem(1, 0, QTableWidgetItem("改變精煉值"))
            table.setItem(1, 1, QTableWidgetItem(str(info["ChangeRefineValue"])))

            #table.setItem(2, 0, QTableWidgetItem("是否保留插卡孔"))
            #table.setItem(2, 1, QTableWidgetItem("是" if info["IsEmptySocket"] else "否"))

            #table.setItem(3, 0, QTableWidgetItem("保留卡片/附魔"))
            #table.setItem(3, 1, QTableWidgetItem("是" if info["PreserveSocketItem"] else "否"))

            #table.setItem(4, 0, QTableWidgetItem("保留評價階級"))
            #table.setItem(4, 1, QTableWidgetItem("是" if info["PreserveGrade"] else "否"))

            #table.setItem(5, 0, QTableWidgetItem("附魔數量要求"))
            #table.setItem(5, 1, QTableWidgetItem(str(info["NeedOptionNumMin"])))

            v.addWidget(table)

            # 材料表
            mats = info["Material"]
            mat_table = QTableWidget()
            mat_table.setColumnCount(2)
            mat_table.setRowCount(len(mats))
            mat_table.setHorizontalHeaderLabels(["材料名稱", "數量"])
            mat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            mat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            mat_table.verticalHeader().setVisible(False)

            for i, m in enumerate(mats):
                mat_table.setItem(i, 0, QTableWidgetItem(self.resolve_item_name(m["name"])))
                mat_table.setItem(i, 1, QTableWidgetItem(str(m["count"])))

            v.addWidget(mat_table)

            # 說明文字（InformationString = 改造前/後說明）
            # 讓 \n 正確變成 <br>，並包成 HTML
            html_lines = []
            for line in info["InformationString"]:
                line = ro_color_to_html(line)  # ← 轉顏色
                html_lines.append(line)

            html_text = "<br>".join(html_lines)

            lbl2 = QLabel()
            lbl2.setTextFormat(Qt.RichText)
            lbl2.setText(html_text)
            lbl2.setWordWrap(True)

            v.addWidget(lbl2)

            # 找到這個 rid 屬於哪個 ReformItemList key
            group_name = None
            for k, id_list in self.reform_item_list.items():
                if rid in id_list:
                    group_name = k
                    break

            if group_name:
                # 用 ItemDBNameTbl → iteminfo_new 顯示真正名稱
                readable_name = self.resolve_item_name(group_name)
                tab_title = f"{readable_name}"
            else:
                tab_title = f"ID {rid}"

            self.tabs.addTab(tab, tab_title)


# ============================================================
# Main 執行
# ============================================================
def main():
    app = QApplication(sys.argv)

    # iteminfo = parse_lub_file("data/iteminfo_new.lua")
    # itemdb = parse_itemdb_name_tbl("data/ItemDBNameTbl.lua")
    # reform = parse_reform_info("data/ItemReformSystem.lua")
    # reform_item_list = parse_reform_item_list("data/ItemReformSystem.lua")
    # ui = ReformUI(reform, iteminfo, itemdb, reform_item_list)
    # ui.resize(700, 600)
    # ui.show()

    # sys.exit(app.exec())


if __name__ == "__main__":
    main()
