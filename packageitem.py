import re
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QListWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout, QMessageBox ,QListWidgetItem,
)
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractScrollArea
from PySide6.QtWidgets import QCheckBox


# ================================================================
# 解析 packageitem.lub
# ================================================================
def parse_package_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    packages = {}
    pos = 0
    length = len(text)

    while True:
        # 找下一個 [12345]
        start = text.find("[", pos)
        if start == -1:
            break

        end_bracket = text.find("]", start)
        if end_bracket == -1:
            break

        pkg_id = int(text[start+1:end_bracket])

        # 找到 "=" 和 第一個 "{"
        eq = text.find("=", end_bracket)
        brace_start = text.find("{", eq)
        if brace_start == -1:
            break

        # 解析成對 {}（手動堆疊）
        depth = 0
        i = brace_start
        while i < length:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
            i += 1

        body = text[brace_start: brace_end+1]

        # --------------------------
        # 解析 body 裡的單個物品條目
        # --------------------------
        entries = re.findall(
            r"{\s*id\s*=\s*(\d+)\s*,\s*prob\s*=\s*(\d+)\s*,\s*name\s*=\s*\"([^\"]*)\"\s*,\s*group\s*=\s*(\d+)\s*}",
            body
        )

        item_list = []
        for id_, prob, name, group in entries:
            item_list.append({
                "id": int(id_),
                "prob": int(prob),
                "name": name,
                "group": int(group)
            })

        packages[pkg_id] = item_list

        pos = brace_end + 1  # 繼續往下找

    return packages



# ================================================================
# 計算 group 機率
# ================================================================
def calculate_probabilities(items):
    groups = {}

    # 分組累計
    for it in items:
        g = it["group"]
        groups.setdefault(g, 0)
        groups[g] += it["prob"]

    # 計算機率
    for it in items:

        # ★ group=0 → 必定獲得 ★
        if it["group"] == 0:
            it["chance"] = 100.0
            continue

        total = groups[it["group"]]

        if total == 0:
            it["chance"] = 100.0
        else:
            it["chance"] = it["prob"] / total * 100

    return items


def build_display_name(pkg_name, info_name, item_id):
    """
    pkg_name: packageitem.lub 的 name（含韓文和可能的數量）
    info_name: iteminfo 找到的中文名稱；若沒找到會等於 pkg_name
    """

    # ==========================================================
    # Case 1：未關聯 → 使用韓文原文，不做數量解析
    # ==========================================================
    if info_name == pkg_name:
        return f"(ID: {item_id}) {pkg_name}"

    # ==========================================================
    # Case 2：有中文 → 使用 prefix + 中文名稱，並解析 15개
    # ==========================================================

    import re

    # 找強化 +7 +8 +9
    refine = re.findall(r"\+\d+", pkg_name)

    # 找卡片標記 [A][B][C][D][N]
    cards = re.findall(r"\[([^\]]+)\]", pkg_name)
    cards = [f"[{c}]" for c in cards if c in {"A", "B", "C", "D", "N"}]

    prefix = " ".join(refine + cards)

    # ------------------------
    # 解析「數字 + 개」
    # ------------------------
    qty_match = re.search(r"(\d+)\s*개", pkg_name)
    qty_text = ""

    if qty_match:
        qty = int(qty_match.group(1))
        qty_text = f" x{qty}"

    # ------------------------
    # 組合顯示名稱
    # ------------------------
    if prefix:
        return f"{prefix} {info_name}{qty_text}"

    return f"{info_name}{qty_text}"


# ================================================================
# 將 iteminfo 的顯示名稱附加到 items
# ================================================================
def attach_display_names(items, parsed_iteminfo):
    for it in items:
        item_id = it["id"]
        pkg_name = it["name"]

        # 中文名稱 or 原文
        if item_id in parsed_iteminfo:
            info_name = parsed_iteminfo[item_id]["name"]
        else:
            info_name = pkg_name  # 未關聯 → 原文

        # *** 使用新版 build_display_name ***
        it["display_name"] = build_display_name(pkg_name, info_name, item_id)

    return items



# ================================================================
# UI 介面
# ================================================================
class PackageViewer(QWidget):
    def __init__(self, package_path, iteminfo_path):
        super().__init__()

        self.packages = parse_package_file(package_path)
        self.parsed_items = parse_lub_file(iteminfo_path)

        self.init_ui()

    def adjust_left_list_width(self):
        fm = self.list_packages.fontMetrics()
        max_width = 0

        for i in range(self.list_packages.count()):
            item = self.list_packages.item(i)
            text_width = fm.horizontalAdvance(item.text())
            if text_width > max_width:
                max_width = text_width

        # 加一點 padding 讓文字不貼邊
        max_width += 20

        # 設定 ListWidget 的寬度
        self.list_packages.setMinimumWidth(max_width)
        self.list_packages.setMaximumWidth(max_width)

    def init_ui(self):
        layout = QHBoxLayout(self)

        # 左側 layout
        left_layout = QVBoxLayout()

        # 搜尋框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋物品名稱...")
        self.search_box.textChanged.connect(self.filter_list)

        # 勾選框
        self.checkbox_replaced = QCheckBox("只顯示TWRO")
        self.checkbox_replaced.stateChanged.connect(self.filter_list)

        # 搜尋列（水平）
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.checkbox_replaced)

        left_layout.addLayout(search_layout)

        # 左側列表
        self.list_packages = QListWidget()
        self.list_packages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_layout.addWidget(self.list_packages)

        # 把左側 layout 放入主 layout
        layout.addLayout(left_layout, 1)

        # 右側表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["物品名稱", "機率 %"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 100)

        layout.addWidget(self.table, 3)


        # 填入所有 package id
        for pkg_id in sorted(self.packages.keys()):

            # 若 iteminfo 有對應的中文（通常是箱子自己的 ID）
            if pkg_id in self.parsed_items:
                # 使用 iteminfo 的中文名稱
                info_name = self.parsed_items[pkg_id]["name"]
                name = f"(ID:{pkg_id}) {info_name}"
            else:
                # 無對應中文 → 只顯示 ID
                name = f"(ID:{pkg_id})"

            item = QListWidgetItem(name)
            item.setData(32, pkg_id)
            self.list_packages.addItem(item)




        # 點擊事件
        self.list_packages.currentItemChanged.connect(self.on_pkg_selected)

        self.setWindowTitle("箱子物品查詢器")
        self.resize(900, 600)
        self.adjust_left_list_width()

    # ============================================================
    # 當左邊選擇 Package ID 時
    # ============================================================
    def on_pkg_selected(self):
        if not self.list_packages.currentItem():
            return

        text = self.list_packages.currentItem().text()
        pkg_id = self.list_packages.currentItem().data(32)  # 取第一個欄位

        items = self.packages[pkg_id]
        items = calculate_probabilities(items)
        items = attach_display_names(items, self.parsed_items)

        self.table.setRowCount(len(items))

        for row, it in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(it["display_name"]))
            chance_text = "必定獲得" if it["chance"] == 100 else f"{it['chance']:.3f}%"
            self.table.setItem(row, 1, QTableWidgetItem(chance_text))

        # 計算所有 group 的總 prob
        group_totals = {}

        for it in items:
            g = it["group"]
            group_totals[g] = group_totals.get(g, 0) + it["prob"]

        # 印出所有 group 的 prob 總和
        # print(f"物品: {pkg_id}")
        # for g, total in sorted(group_totals.items()):
        #     print(f"  group {g} prob總和 = {total}")



    def filter_list(self, text=None):
        # 搜尋文字
        text = self.search_box.text().lower().strip()

        # 是否只顯示有中文（已替換）
        only_replaced = self.checkbox_replaced.isChecked()

        for i in range(self.list_packages.count()):
            item = self.list_packages.item(i)
            pkg_id = item.data(32)
            name = item.text().lower()

            # 搜尋條件
            match_search = (text in name) or (text in str(pkg_id))

            # 勾選後 → 只顯示 parsed_items 內有中文名稱的
            if only_replaced:
                has_chinese = pkg_id in self.parsed_items
            else:
                has_chinese = True   # 不篩選

            item.setHidden(not (match_search and has_chinese))




def clean_display_name(name):
    """
    只保留:
    - +7 +8 +9...
    - [A][B][C][D][N] 卡片標記
    其餘中文字、數字全部保留
    """

    # 只允許真正的卡片前綴
    prefix = re.findall(r"\+\d+|\[(A|B|C|D|N)\]", name)

    # 若有真正的強化或卡片前綴 → 回傳：prefix + 原名(去韓文)
    if prefix:
        # 把韓文去掉即可（保留所有中文）
        name_no_korean = re.sub(r"[\uac00-\ud7af]+", "", name).strip()
        return " ".join(prefix) + " " + name_no_korean

    # 沒 prefix → 回傳原名（去韓文）
    name_no_korean = re.sub(r"[\uac00-\ud7af]+", "", name).strip()
    return name_no_korean

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


# ================================================================
# 主程式
# ================================================================
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # 請自行設定你的檔案路徑
    packageitem_path = "data/packageitem.lua"
    iteminfo_path = "data/iteminfo_new.lua"

    viewer = PackageViewer(packageitem_path, iteminfo_path)
    viewer.show()

    sys.exit(app.exec())
