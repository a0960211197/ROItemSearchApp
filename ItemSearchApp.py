#部分資料取自ROCalculator,搜尋 ROCalculator 可以知道哪些有使用


import sys, builtins, time
from PySide6.QtCore import QThread, Signal, Qt, QMetaObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QPlainTextEdit, QLabel



class InitWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(str)
    done_signal = Signal(object)
    
    def __init__(self, app_instance=None):
        super().__init__()
        self.app_instance = app_instance  # 接收主程式的物件

    def run(self):
        original_print = builtins.print

        def custom_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            end = kwargs.get("end", "\n")

            if end == "\r":
                self.progress_signal.emit(msg)
            else:
                self.log_signal.emit(msg)

            # ✅ 同時即時印出（不等事件迴圈）
            original_print(*args, **kwargs, flush=True)


        builtins.print = custom_print

        try:
            print("開始載入資料...")
            data = None
            if self.app_instance:
                data = self.app_instance.dataloading()
            print("載入完成！")
            self.done_signal.emit(data) 
        except Exception as e:
            print(f"初始化發生錯誤：{e}")
        finally:
            builtins.print = original_print



class LoadingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("初始化中…")
        self.resize(500, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        self.label = QLabel("正在載入資料，請稍候...")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        layout.addWidget(self.label)
        layout.addWidget(self.text)

    def append_text(self, msg: str):
        self.text.appendPlainText(msg)

    def update_progress(self, msg: str):
        self.label.setText(msg)



import os
import subprocess

def compile_ui_files(ui_dir="UI"):
    """
    將 ui_dir 資料夾下的所有 .ui 檔案轉換成 .py
    """
    for file in os.listdir(ui_dir):
        if file.endswith(".ui"):
            ui_path = os.path.join(ui_dir, file)
            py_path = os.path.splitext(ui_path)[0] + ".py"

            # 呼叫 pyside6-uic
            cmd = ["pyside6-uic", ui_path, "-o", py_path]
            print(f"[UI] 轉換 {ui_path} → {py_path}")
            try:
                subprocess.run(cmd, check=True, shell=True)
            except Exception as e:
                print(f"[UI] 轉換失敗: {e}")

# === 主程式執行前，先自動轉換 UI ===
compile_ui_files()

import importlib.util
import sys
import re
import subprocess
import os
import json
import math
from collections import defaultdict
import pandas as pd
from PySide6.QtCore import Qt,QThread, Signal ,QTimer, QPoint
from PySide6.QtGui import QFont ,QAction,QIntValidator,QPalette, QColor
from sympy import sympify, symbols, Symbol
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel,QGroupBox, QToolButton,QSizePolicy,
    QComboBox, QTextEdit, QMessageBox, QHBoxLayout, QScrollArea, QCheckBox, QMenuBar, QFileDialog,
    QPushButton, QTabWidget, QFormLayout, QSpinBox  ,QDoubleSpinBox  ,QFrame , QGridLayout,QDialog, QListWidget,
)


enabled_skill_levels = {}  # 存放已啟用技能的等級
global_weapon_level_map = {}#武器等級
global_armor_level_map = {}#防具等級
global_weapon_type_map = {}#武器類型
function_defs = {}#公式變數字典
def register_function(name, desc, args):
    if name in function_defs:
        return  # 已經有了就跳過
    function_defs[name] = {
        "desc": desc,
        "args": args
    }


#外部技能物品BUFF
file_path = os.path.join("data", "all_skill_entries.py")
spec = importlib.util.spec_from_file_location("all_skill_entries", file_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
all_skill_entries = module.all_skill_entries



effect_map = {
    41: "ATK", 45: "DEF", 47: "MDEF", 49: "HIT", 50: "FLEE", 51: "完全迴避", 52: "CRI", 54: "ASPD",
    103: "STR", 104: "AGI", 105: "VIT", 106: "INT", 107: "DEX", 108: "LUK",
    109: "MHP", 110: "MSP", 111: "MHP%", 112: "MSP%", 113: "HP自然恢復%", 114: "SP自然恢復%",
    140: "MATK%", 167: "攻擊後延遲", 200: "MATK", 207: "ATK%",
    234: "POW", 235: "STA", 236: "WIS", 237: "SPL", 238: "CON", 239: "CRT",
    242: "P.ATK", 243: "S.MATK", 244: "RES", 245: "MRES",
    253: "C.RATE", 254: "H.PLUS"
}
element_map = {
    0: "無屬性",
    1: "水屬性",
    2: "地屬性",
    3: "火屬性",
    4: "風屬性",
    5: "毒屬性",
    6: "聖屬性",
    7: "暗屬性",
    8: "念屬性",
    9: "不死屬性",
    10: "全屬性",
    999: "（不使用）"
}

size_map = {
    0: "小型",
    1: "中型",
    2: "大型"
}

race_map = {
    0: "無形",
    1: "不死",
    2: "動物",
    3: "植物",
    4: "昆蟲",
    5: "魚貝",
    6: "惡魔",
    7: "人形",
    8: "天使",
    9: "龍族",
    10: "玩家（人類）",
    11: "玩家（貓族）",
    9999: "全種族"
}

unit_map = {
    0: "玩家",
    1: "魔物"
}

class_map = {
    0: "一般",
    1: "首領",
    2: "玩家"
}

#職業名稱跟JOB補正#ROCalculator
job_dict = {
    4252: {"name": "盧恩龍爵", "TJobMaxPoint": [6,8,7,8,8,6,10,6,3,5,6,8]},
    4253: {"name": "機甲神匠", "TJobMaxPoint": [10,6,10,6,5,6,9,10,5,0,7,7]},
    4254: {"name": "十字影武", "TJobMaxPoint": [8,11,6,5,9,4,12,8,4,0,7,7]},
    4255: {"name": "禁咒魔導士", "TJobMaxPoint": [1,7,8,15,8,4,0,8,7,13,9,1]},
    4256: {"name": "樞機主教", "TJobMaxPoint": [6,7,7,12,7,4,8,5,5,9,4,7]},
    4257: {"name": "風鷹狩獵者", "TJobMaxPoint": [2,12,8,9,8,4,9,5,5,4,11,4]},
    4258: {"name": "帝國聖衛軍", "TJobMaxPoint": [9,3,9,10,9,3,7,11,6,7,4,3]},
    4259: {"name": "生命締造者", "TJobMaxPoint": [5,6,8,12,8,4,7,4,4,4,7,12]},
    4260: {"name": "深淵追跡者", "TJobMaxPoint": [8,9,8,6,6,6,8,8,4,7,5,6]},
    4261: {"name": "元素支配者", "TJobMaxPoint": [4,4,8,13,9,5,3,8,7,12,5,3]},
    4262: {"name": "聖裁者", "TJobMaxPoint": [10,10,6,8,8,1,11,8,5,3,5,6]},
    4263: {"name": "天籟頌者", "TJobMaxPoint": [7,7,7,9,10,3,6,7,4,6,11,4]},
    4264: {"name": "樂之舞靈", "TJobMaxPoint": [7,9,6,10,8,3,6,7,4,6,11,4]},
    4308: {"name": "魂靈師", "TJobMaxPoint": [5,7,5,9,12,5,8,6,5,8,7,4]},
    4307: {"name": "終極初學者", "TJobMaxPoint": [10,5,6,10,5,6,9,5,4,9,8,3]},
    4306: {"name": "夜行者", "TJobMaxPoint": [3,8,6,8,11,7,11,6,5,0,10,5]},
    4304: {"name": "流浪忍者", "TJobMaxPoint": [10,12,6,4,9,3,10,10,4,0,6,8]},
    4305: {"name": "疾風忍者", "TJobMaxPoint": [4,8,5,10,10,3,4,8,10,3,6,7]},
    4303: {"name": "契靈士", "TJobMaxPoint": [3,7,7,11,13,2,0,8,7,16,7,3]},
    4302: {"name": "天帝", "TJobMaxPoint": [12,10,6,3,9,3,12,10,2,0,6,7]},
}

stat_name_sets  = {#裝備基礎編碼
    "armor": [
        "DEF", "STR", "AGI", "VIT", "INT", "DEX", "LUK", "未知7", "未知8",
        "MDEF", "防具等級", "POW", "STA", "WIS", "SPL", "CON", "CRT"
    ],
    "Mweapon": [
        "武器屬性", "武器類型", "武器ATK", "武器MATK", "STR", "INT", "VIT", "DEX", "AGI",
        "LUK", "武器等級", "未知11", "未知12", "未知13", "未知14", "未知15", "未知16"
    ],
    "Rweapon": [
        "武器類型", "武器ATK", "STR", "INT", "VIT", "DEX", "AGI", "LUK", "武器等級",
        "未知9", "未知10", "未知11", "未知12", "未知13", "未知14"
    ],
    "ammo": [
        "屬性", "箭矢/彈藥ATK"
    ]
}


weapon_type_map = {
    1: "短劍", 2: "單手劍", 3: "雙手劍", 4: "單手矛", 5: "雙手矛",
    6: "單手斧", 7: "雙手斧", 8: "鈍器", 10: "單手仗", 12: "拳套",
    13: "樂器", 14: "鞭子", 15: "書", 16: "拳刃", 23: "雙手仗",
    11: "弓", 17: "左輪手槍", 18: "來福槍", 19: "格林機關槍",
    20: "霰彈槍", 21: "榴彈槍", 22: "風魔飛鏢"
}

weapon_class_codes = {#輸出用
    0: "Empty",# 空手
    1: "Daggers",  # 短劍
    2: "OneHandedSwords",  # 單手劍
    3: "TwoHandedSword",  # 雙手劍
    4: "Spears",  # 單手矛
    5: "Spears",  # 雙手矛
    6: "Axes",  # 單手斧
    7: "Axes",  # 雙手斧
    8: "Maces",  # 鈍器
    10: "Rods",  # 單手仗
    11: "Bows",  # 弓
    12: "Knuckles",  # 拳套
    13: "Instruments",  # 樂器
    14: "Whips",  # 鞭子
    15: "Books",  # 書
    16: "Katars",  # 拳刃
    17: "Guns",  # 左輪手槍
    18: "Guns",  # 來福槍
    19: "Guns",  # 格林機關槍
    20: "Guns",  # 霰彈槍
    21: "Guns",  # 榴彈槍
    22: "Shuriken",  # 風魔飛鏢
    23: "Rods",  # 雙手仗
}
#weapon_class
weapon_type_size_penalty = {#物體武器體型修正
    0: [100, 100, 100],# 空手
    1: [100, 75, 50],  # 短劍
    2: [75, 100, 75],  # 單手劍
    3: [75, 75, 100],  # 雙手劍
    4: [75, 75, 100],  # 單手矛
    5: [75, 75, 100],  # 雙手矛
    6: [50, 75, 100],  # 單手斧
    7: [50, 75, 100],  # 雙手斧
    8: [75, 100, 100],  # 鈍器
    10: [100, 100, 100],  # 單手仗
    11: [100, 100, 75],  # 弓
    12: [100, 100, 75],  # 拳套
    13: [75, 100, 75],  # 樂器
    14: [75, 100, 50],  # 鞭子
    15: [100, 100, 50],  # 書
    16: [75, 100, 75],  # 拳刃
    17: [100, 100, 100],  # 左輪手槍
    18: [100, 100, 100],  # 來福槍
    19: [100, 100, 100],  # 格林機關槍
    20: [100, 100, 100],  # 霰彈槍
    21: [100, 100, 100],  # 榴彈槍
    22: [75, 75, 100],  # 風魔飛鏢
    23: [100, 100, 100],  # 雙手仗

}




excluded_stat_names = {#過濾不顯示到效果
    "防具等級",
    }

# 定義多組排序規則
custom_sort_orders = {
    "增傷詞條": [
        "ATK",
        "MATK",
        "P.ATK",
        "S.MATK",
        "屬性 的",
        "小型",
        "中型",
        "大型",
        "全種族",
        "型怪",
        "全屬性",
        "對象",
        "階級",
        "距離",
        "防禦",
        "技能",
        "詠唱",
    ],
    "ROCalculator輸入": [
        "STR",
        "AGI",
        "VIT",
        "INT",
        "DEX",
        "LUK",
        "POW",
        "STA",
        "WIS",
        "SPL",
        "CON",
        "CRT",
        "技能",
        "CRI",
        "P.ATK",
        "S.MATK",
        "ATK",
        "全種族",
        "型怪",
        "小型",
        "中型",
        "大型",
        "階級",
        "全屬性",
        "對象",
        "魔法傷害",
        "爆擊傷害",
        "C.RATE",
        "距離",
    ],
}

def get_custom_sort_value(key, sort_mode):
    """依照指定 sort_mode 的順序表來決定排序位置"""
    order_list = custom_sort_orders.get(sort_mode, [])
    for idx, keyword in enumerate(order_list):
        if keyword in key:
            return idx
    return len(order_list)  # 沒找到的放最後


# 屬性倍率表（level, attacker, defender）

# Lv1 ~ Lv4 相剋表（依 element_map 順序）
damage_tables = {
    1: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  90, 100],
        [100,  25, 100, 150,  90, 150, 100, 100, 100, 100],
        [100, 100,  25,  90, 150, 150, 100, 100, 100, 100],
        [100,  90, 150,  25, 100, 150, 100, 100, 100, 125],
        [100, 150,  90, 100,  25, 150, 100, 100, 100, 100],
        [100, 150, 150, 150, 150,   0,  75,  75,  75,  75],
        [100, 100, 100, 100, 100,  75,   0, 125, 100, 125],
        [100, 100, 100, 100, 100,  75, 125,   0, 100,   0],
        [ 90, 100, 100, 100, 100,  75,  90,  90, 125, 100],
        [100,  90, 100, 100, 100,  75, 125,   0, 100,   0],
    ],
    2: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  70, 100],
        [100,   0, 100, 175,  80, 150, 100, 100, 100, 100],
        [100, 100,   0,  80, 175, 150, 100, 100, 100, 100],
        [100,  80, 175,   0, 100, 150, 100, 100, 100, 150],
        [100, 175,  80, 100,   0, 150, 100, 100, 100, 100],
        [100, 150, 150, 150, 150,   0,  75,  75,  75,  50],
        [100, 100, 100, 100, 100,  75,   0, 150, 100, 150],
        [100, 100, 100, 100, 100,  75, 150,   0, 100,   0],
        [ 70, 100, 100, 100, 100,  75,  80,  80, 150, 125],
        [100,  80, 100, 100, 100,  50, 150,   0, 125,   0],
    ],
    3: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,  50, 100],
        [100,   0, 100, 200,  70, 125, 100, 100, 100, 100],
        [100, 100,   0,  70, 200, 125, 100, 100, 100, 100],
        [100,  70, 200,   0, 100, 125, 100, 100, 100, 175],
        [100, 200,  70, 100,   0, 125, 100, 100, 100, 100],
        [100, 125, 125, 125, 125,   0,  50,  50,  50,  25],
        [100, 100, 100, 100, 100,  50,   0, 175, 100, 175],
        [100, 100, 100, 100, 100,  50, 175,   0, 100,   0],
        [ 50, 100, 100, 100, 100,  50,  70,  70, 175, 150],
        [100,  70, 100, 100, 100,  25, 175,   0, 150,   0],
    ],
    4: [ #無   水   地    火   風   毒    聖    暗   念  不死
        [100, 100, 100, 100, 100, 100, 100, 100,   0, 100],
        [100,   0, 100, 200,  60, 125, 100, 100, 100, 100],
        [100, 100,   0,  60, 200, 125, 100, 100, 100, 100],
        [100,  60, 200,   0, 100, 125, 100, 100, 100, 200],
        [100, 200,  60, 100,   0, 125, 100, 100, 100, 100],
        [100, 125, 125, 125, 125,   0,  50,  50,  50,   0],
        [100, 100, 100, 100, 100,  50,   0, 200, 100, 200],
        [100, 100, 100, 100, 100,  50, 200,   0, 100,   0],
        [  0, 100, 100, 100, 100,  50,  60,  60, 200, 175],
        [100,  60, 100, 100, 100,   0, 200,   0, 175,   0],
    ]
}


equipid_mapping = {#主程式equip to ROCalculator 轉換
    "equip_STR": "STR",
    "equip_AGI": "AGI",
    "equip_VIT": "VIT",
    "equip_INT": "INT",
    "equip_DEX": "DEX",
    "equip_LUK": "LUK",
    "equip_POW": "POW",
    "equip_STA": "STA",
    "equip_WIS": "WIS",
    "equip_SPL": "SPL",
    "equip_CON": "CON",
    "equip_CRT": "CRT",
    "Use_Skills": "SkillDamagePercent",
    #魔法
    "SMATK": "SMATK",
    "MATK_armor": "Matk",
    "MATK_percent": "MatkPercent",
    "RaceMatkPercent": "RaceMatkPercent",
    "SizeMatkPercent": "SizeMatkPercent",
    "LevelMatkPercent": "LevelMatkPercent",
    "ElementalMatkPercent": "ElementalMatkPercent",
    "ElementalMagicPercent": "ElementalMagicPercent",

    #物理
    "PATK": "PATK",
    "CRATE":"CRIDR",
    "ATK_armor": "Atk",
    "ATK_percent": "AtkPercent",
    "RaceAtkPercent": "RaceAtkPercent",
    "SizeAtkPercent": "SizeAtkPercent",
    "LevelAtkPercent": "LevelAtkPercent",
    "ElementalAtkPercent": "ElementalAtkPercent",
    "Damage_CRI": "CriDamagePercent",
    "MeleeAttackDamage": "MeleeDamagePercent",
    "RangeAttackDamage": "RangedDamagePercent",
    
}

status_mapping = {#主程式status to ROCalculator 轉換
    "BaseLv": "Level",
    "JobLv": "JOBLevel",
    "base_STR": "STR",
    "base_AGI": "AGI",
    "base_VIT": "VIT",
    "base_INT": "INT",
    "base_DEX": "DEX",
    "base_LUK": "LUK",
    "base_POW": "POW",
    "base_STA": "STA",
    "base_WIS": "WIS",
    "base_SPL": "SPL",
    "base_CON": "CON",
    "base_CRT": "CRT",
}

weapon_mapping = {#主程式weapon to ROCalculator 轉換
    "weapon_codes": ("type", "id"),
    "weapon_Level": ("level", "id"),
    "weaponGradeR": ("grade", "id"),
    "ATK_Mweapon": "ATK",
    "MATK_Mweapon": "MATK",
    "weaponRefineR": "refinelevel",
    "ammoATK": "ArrowATK"
}



TSTATUS_POINT_COSTS = [#取自ROCalculator(特性數值點術
    7,10,13,16,19,26,29,32,35,38,
    45,48,51,54,57,64,67,70,73,76,
    83,86,89,92,95,102,105,108,111,114,
    121,124,127,130,133,140,143,146,149,152,
    159,162,165,168,171,178,181,184,187,190,
    197,200,203,206,209,216,219,222,225,235
]


from PySide6.QtWidgets import QDialog
from UI.ui_savemanager import Ui_SaveManagerDialog

class SaveManagerDialog(QDialog, Ui_SaveManagerDialog):#儲存裝被選則
    def __init__(self, part_name, save_list, on_delete, parent=None):
        super().__init__(parent)
        self.setupUi(self)   # 這裡載入 Designer 畫的 UI

        self.setWindowTitle(f"{part_name} 的裝備清單")
        self.part_name = part_name
        self.save_list = save_list
        self.selected_save = None
        self.on_delete = on_delete

        self.listWidget.addItems(self.save_list)
        self.loadButton.clicked.connect(self.load_selected)
        self.deleteButton.clicked.connect(self.delete_selected)
        self.cancelButton.clicked.connect(self.reject)
        self.listWidget.itemDoubleClicked.connect(self.load_selected)


    def load_selected(self, item=None):
        if item:  # 如果是雙擊傳進來的 item
            self.selected_save = item.text()
            self.accept()
        else:  # 如果是按下按鈕呼叫
            current_item = self.listWidget.currentItem()
            if current_item:
                self.selected_save = current_item.text()
                self.accept()

    def delete_selected(self):
        current_item = self.listWidget.currentItem()
        if current_item:
            save_name = current_item.text()
            confirm = QMessageBox.question(
                self,
                "確認刪除",
                f"確定要刪除存檔「{save_name}」嗎？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                # 👇 呼叫主程式的刪除邏輯
                self.on_delete(self.part_name, save_name)

                # 從清單移掉
                self.save_list.remove(save_name)
                self.listWidget.takeItem(self.listWidget.row(current_item))




#取自ROCalculator特性數值點數計算
def get_total_tstat_points(level: int) -> int:
    index = level - 200
    if index < 0:
        return 0
    if index >= len(TSTATUS_POINT_COSTS):
        return TSTATUS_POINT_COSTS[-1]
    return TSTATUS_POINT_COSTS[index]


# 初始化技能映射變數
skill_map = {}
skill_map_all = {}

def load_skill_map(filepath=None):
    global skill_map, skill_map_all, skill_df
    try:
        if filepath is None or isinstance(filepath, bool):
            filepath = r"data\skillneme.csv"

        skill_df = pd.read_csv(filepath, header=0)
        skill_map = dict(zip(skill_df["ID"], skill_df["Name"]))
        skill_map_all = skill_df.set_index("ID").to_dict(orient="index")
        #self.replace_custom_calc_content()
        print("技能列表已成功載入")
    except Exception as e:
        skill_map = {}
        skill_map_all = {}
        print(f"載入技能列表失敗：{e}")


load_skill_map() #讀取SKILL列表


def parse_lua_effects_with_variables(
    block_text,
    refine_inputs,
    get_values,
    grade,
    unit_map,
    size_map,
    effect_map,
    hide_unrecognized=False,
    hide_physical=False,
    hide_magical=False,
    current_location_slot=None
):
    lines = block_text.splitlines()
    variables = {}
    sfct_handled = False  # ✅ 控制是否已處理過 SubSFCTEquipAmount
    skill_delay_accum = {}
    results = []
    condition_met = True
    indent_stack = []
    weapon_level_map = variables.setdefault("__weapon_level_map__", {})


    safe_globals = {"__builtins__": None}
    safe_locals = {"math": __import__("math")}
    def safe_eval_expr(expr, variables, get_values, refine_inputs, grade):
        expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
        expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
        expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)

        # 將變數名稱替換成實際數值
        for v in sorted(variables.keys(), key=lambda x: -len(x)):
            expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)

        # 補括號
        if expr.count("(") > expr.count(")"):
            expr += ")" * (expr.count("(") - expr.count(")"))

        try:
            # 把 math 跟 temp 等變數放進 local 環境
            safe_locals = {"math": __import__("math")}
            safe_locals.update(variables)
            return int(eval(expr, {"__builtins__": None}, safe_locals))
        except Exception as e:
            return f"{expr}（無法解析）"

    
    
    

    

    for line in lines:
        original_line = line.strip()
        line = original_line.split("--")[0].strip()
        # 把 GetRefineLevel(GetLocation()) 轉為當前部位的 slot ID
        if current_location_slot is not None:
            refine_value = refine_inputs.get(current_location_slot, 0)
            line = re.sub(
                r"GetRefineLevel\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(refine_value),
                line
            )
            # 從全域變數中抓出該部位的武器等級
            if current_location_slot not in global_weapon_level_map:
                global_weapon_level_map[current_location_slot] = 0
            weapon_level = global_weapon_level_map.get(current_location_slot, 0)

            line = re.sub(
                r"GetEquipWeaponLv\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(weapon_level),
                line
            )
            # 從全域變數中抓出該部位的防具等級
            if current_location_slot not in global_armor_level_map:
                global_armor_level_map[current_location_slot] = 0
            armor_level = global_armor_level_map.get(current_location_slot, 0)
            line = re.sub(
                r"GetEquipArmorLv\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(armor_level),
                line
            )
            #從全域變數抓出技能等級
            line = re.sub(
                r"GetSkillLevel\((\d+)\)",
                lambda m: str(enabled_skill_levels.get(int(m.group(1)), 0)),
                line
            )
            # 從全域變數抓出該部位的武器類型（代碼）
            if current_location_slot not in global_weapon_type_map:
                global_weapon_type_map[current_location_slot] = 0
            weapon_class = global_weapon_type_map.get(current_location_slot, 0)

            line = re.sub(
                r"GetWeaponClass\s*\(\s*GetLocation\s*\(\s*\)\s*\)",
                str(weapon_class),
                line
            )

        if not line:
            continue
            
        # === 特殊判斷：若為 P.S = XXX 則直接顯示後面的文字 ===
        if line.startswith("P.S ="):
            comment = line.split("=", 1)[1].strip()
            results.append(f"P.S：{comment}")
            continue
        # 🔽  GetPetRelationship() 替換為傳入的裝備階級
        line = re.sub(r"GetPetRelationship\s*\(\s*\)", str(grade), line)

        # 將 GetEquipGradeLevel(GetLocation()) 替換為傳入的裝備階級
        line = re.sub(r"GetEquipGradeLevel\s*\(\s*GetLocation\s*\(\s*\)\s*\)", str(grade), line)
        # 補充解析 Type 與 Stat 同行的情況（裝備類別與屬性）
        type_stat_match = re.match(r'Type\s*=\s*"(.*?)"\s*,\s*Stat\s*=\s*\{(.*?)\}', line)
        if type_stat_match:
            eq_type = type_stat_match.group(1)
            stat_str = type_stat_match.group(2)
            stat_values = [int(x.strip()) for x in stat_str.split(",")]
            stat_names_list = stat_name_sets.get(eq_type, stat_name_sets["armor"])

            results.append(f"🛠️ 類型：{eq_type}")
            for idx, val in enumerate(stat_values):
                if val != 0:
                    name = stat_names_list[idx] if idx < len(stat_names_list) else f"未知{idx}"
                    results.append(f"{name} +{val}")
            continue




        # 處理單行 Stat = {...}
        stat_match = re.search(r'Stat\s*=\s*\{([^\}]+)\}', line)
        if stat_match:
            stat_values = [int(x.strip()) for x in stat_match.group(1).split(",") if x.strip().isdigit()]

            # 嘗試在整體文本中找到 Type
            type_match = re.search(r'Type\s*=\s*"(\w+)"', block_text)
            equip_type = type_match.group(1) if type_match else "armor"
            stat_names = stat_name_sets.get(equip_type, stat_name_sets["armor"])

            for idx, val in enumerate(stat_values):
                if val != 0:
                    stat_name = stat_names[idx] if idx < len(stat_names) else f"未知{idx}"

                    # 儲存武器或防具等級
                    if stat_name == "武器等級":
                        global_weapon_level_map[current_location_slot] = val
                    elif stat_name == "防具等級":
                        global_armor_level_map[current_location_slot] = val
                        
                    # ✅ 處理武器類型（使用 map 轉換中文名稱）
                    if stat_name == "武器類型":
                        global_weapon_type_map[current_location_slot] = val
                        weapon_type_name = weapon_type_map.get(val, f"未知武器類型({val})")
                        results.append(f"武器類型：{weapon_type_name}")
                        #continue  # 若你不想再輸出 "武器類型 +x" 可跳過

                    # 過濾排除屬性
                    if stat_name in excluded_stat_names:
                        continue

                    results.append(f"{stat_name} +{val}")



        # 1. EnableSkill(skill_id, level)
        register_function("EnableSkill", "可使用技能", [
            {"name": "技能", "map": "skill_map"},
            {"name": "等級", "type": "value"}
        ])
        enable_skill = re.match(r"EnableSkill\((\d+),\s*(\d+)\)", line)
        if enable_skill and condition_met:
            skill_id, level = enable_skill.groups()
            skill_id = int(skill_id)
            level = int(level)
            skill_name = skill_map.get(skill_id, f"技能ID {skill_id}")
            results.append(f"可使用【{skill_name}】Lv.{level}")
            # ➕ 記錄技能等級
            enabled_skill_levels[skill_id] = level
            continue

        # 紀錄目前是否已有 if/elseif 成立（for this level）
        skip_branch = False

        # 處理 if 條件判斷
        if_match = re.match(r"if\s+(.+?)\s+then", line)
        if if_match:
            expr = if_match.group(1)
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)
                
            # ✅ Lua ➜ Python 條件語法轉換
            expr = expr.replace("~=", "!=")
            expr = expr.replace(" and ", " and ")
            expr = expr.replace(" or ", " or ")
            expr = expr.replace(" not ", " not ")
            try:
                result = eval(expr, safe_globals, safe_locals)
                condition_met = bool(result)
                results.append(f"{'✅條件成立' if condition_met else '❌條件不成立'} : {if_match.group(1)}")
            except Exception as e:
                condition_met = False
                results.append(f"⚠️ 無法解析條件: {if_match.group(1)}，錯誤: {e}")
            indent_stack.append(condition_met)
            continue

        # elseif 判斷
        elseif_match = re.match(r"elseif\s+(.+?)\s+then", line)
        if elseif_match:
            if indent_stack and indent_stack[-1] is True:
                # 上一層條件已成立，這一層不執行
                indent_stack.append(False)
                condition_met = False
                continue
            expr = elseif_match.group(1)
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)
            try:
                result = eval(expr, safe_globals, safe_locals)
                condition_met = bool(result)
                results.append(f"{'✅' if condition_met else '❌'} 條件成立: {expr}")
            except Exception as e:
                condition_met = False
                results.append(f"⚠️ 無法解析條件: {expr}，錯誤: {e}")
            indent_stack.append(condition_met)
            continue

        # else 判斷
        if line.startswith("else"):
            if indent_stack and indent_stack[-1] is True:
                indent_stack.append(False)
                condition_met = False
            else:
                indent_stack.append(True)
                condition_met = True
            continue
            
        if line == "end":
            if indent_stack:
                indent_stack.pop()
            condition_met = all(indent_stack) if indent_stack else True
            continue
        # 新增對 temp = GetRefineLevel(...) 的處理邏輯
        refine_assign = re.match(r"(\w+)\s*=\s*GetRefineLevel\((\d+)\)", line)
        if refine_assign:
            var, slot = refine_assign.groups()
            try:
                value = refine_inputs.get(int(slot), 0)
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetRefineLevel({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetRefineLevel({slot})")
            continue
            
        # 新增對 temp = GetEquipGradeLevel(...) 的處理邏輯
        grade_assign = re.match(r"(\w+)\s*=\s*GetEquipGradeLevel\((\d+)\)", line)
        if grade_assign:
            var, slot = grade_assign.groups()
            try:
                # 如果 grade 是 dict，取對應部位；否則直接用整數
                value = grade.get(int(slot), 0) if isinstance(grade, dict) else grade
                #print(f"[DEBUG] slot {slot} 的 grade 值: {value} 來源: {original_line.strip()}")
                
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（GetEquipGradeLevel({slot})）")
            except:
                results.append(f"⚠️ 無法計算 `{var}` = GetEquipGradeLevel({slot})")
            continue


        # math.floor(...) 指定變數
        var_math = re.match(r"(\w+)\s*=\s*math\.floor\((.+)\)", line)
        if var_math:
            var, expr = var_math.groups()
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            for v in sorted(variables.keys(), key=lambda x: -len(x)):
                expr = re.sub(rf'\b{re.escape(v)}\b', str(variables[v]), expr)
            try:
                value = int(eval(f"math.floor({expr})", safe_globals, safe_locals))
                variables[var] = value
                results.append(f"📌 `{var}` = {value}（floor({expr})）")
            except Exception as e:
                results.append(f"⚠️ 無法計算 `{var}` = floor({expr})，錯誤：{e}")
            continue

        # 一般變數指定
        var_assign = re.match(r"(\w+)\s*=\s*(.+)", line)
        if var_assign and not var_math:
            if not condition_met:
                results.append(f"⛔ 已跳過（條件不成立）: {original_line}")
                continue  # 不執行此行
            var, expr = var_assign.groups()
            if '"' in expr or "'" in expr or "{" in expr or "function" in expr:
                results.append(f"🟡一般變數 無法辨識: {original_line}")
                continue

            # 替換函數式的數值
            expr = re.sub(r"get\((\d+)\)", lambda m: str(get_values.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetRefineLevel\((\d+)\)", lambda m: str(refine_inputs.get(int(m.group(1)), 0)), expr)
            expr = re.sub(r"GetEquipGradeLevel\((\d+)\)", lambda m: str(grade), expr)
            expr = re.sub(
                r"GetSkillLevel\((\d+)\)",
                lambda m: str(enabled_skill_levels.get(int(m.group(1)), 0)),
                expr
            )
            # ✅ 改用 eval + variables 做上下文，不再手動替換
            try:
                value = int(eval(expr, {"__builtins__": None}, variables))
                variables[var] = value
                results.append(f"📌 `{var}` = {value}")
            except Exception as e:
                results.append(f"⚠️ 無法計算 `{var}` = {expr}，錯誤：{e}")
            continue
            
            

        # AddExtParam(...)
        register_function("AddExtParam", "增加基礎能力", [{"name": "無意義", "map": "1"},{"name": "能力", "map": "effect_map"},{"name": "數值", "type": "value"}])
        register_function("SubExtParam", "減少基礎能力", [{"name": "無意義", "map": "1"},{"name": "能力", "map": "effect_map"},{"name": "數值", "type": "value"}])

        # AddExtParam / SubExtParam 合併處理
        ext = re.match(r"(Add|Sub)ExtParam\((\d+),\s*(\d+),\s*(.+)\)", line)
        if ext and condition_met:
            op, unit, param_id, val_expr = ext.groups()
            val = safe_eval_expr(val_expr, variables, get_values, refine_inputs, grade)

            unit_str = unit_map.get(int(unit), f"單位{unit}")
            effect_str = effect_map.get(int(param_id), f"參數{param_id}")

            # 解析失敗保護
            if not isinstance(val, int):
                results.append(f"{effect_str} ({val})（無法解析）")
                continue

            # 預設：Add=+、Sub=-
            def sign_for(op_: str, invert: bool = False) -> str:
                # invert=True 會反轉（給「攻擊後延遲」用）
                return "+" if ((op_ == "Add") != invert) else "-"

            # 特例 1：CRI、完全迴避（每 10 = 1）
            if effect_str in ("CRI", "完全迴避"):
                v = val // 10
                results.append(f"{effect_str} {sign_for(op)}{v}")
                continue

            # 特例 2：攻擊後延遲（Add=減少、Sub=增加）+ 一定加 %
            if effect_str == "攻擊後延遲":
                results.append(f"{effect_str} {sign_for(op, invert=True)}{val}%")
                continue

            # 一般情況：若名稱本身以 % 結尾（如 MATK% / ATK%），就帶 %
            percent_suffix = "%" if str(effect_str).endswith("%") else ""
            results.append(f"{effect_str} {sign_for(op)}{val}{percent_suffix}")
            continue

            
        # AddSpellDelay / SubSpellDelay 合併處理（技能後延遲 %）
        register_function("AddSpellDelay", "增加技能後延遲", [{"name": "數值%", "type": "value"}])
        register_function("SubSpellDelay", "減少技能後延遲", [{"name": "數值%", "type": "value"}])

        delay = re.match(r"(Add|Sub)SpellDelay\(\s*(.+)\s*\)\s*$", line)
        if delay and condition_met:
            op, expr = delay.groups()
            val = safe_eval_expr(expr, variables, get_values, refine_inputs, grade)

            if isinstance(val, int):
                sign = "+" if op == "Add" else "-"
                results.append(f"技能後延遲 {sign}{val}%")
            else:
                # 保留原本的「無法解析」提示
                sign = "+" if op == "Add" else "-"
                results.append(f"技能後延遲 {sign}({val})%（無法解析）")
            continue



        # AddSFCTEquipAmount / SubSFCTEquipAmount（固定詠唱時間，第一參數是 ms 表達式，第二參數是數字）
        register_function("SubSFCTEquipAmount", "減少固定詠唱時間", [
            {"name": "數值ms", "type": "value"},
            {"name": "無意義", "map": "0"}
        ])
        register_function("AddSFCTEquipAmount", "增加固定詠唱時間", [
            {"name": "數值ms", "type": "value"},
            {"name": "無意義", "map": "0"}
        ])

        sfct = re.match(r"(Add|Sub)SFCTEquipAmount\(\s*(.+)\s*,\s*(\d+)\s*\)\s*$", line)
        if sfct and condition_met and not sfct_handled:
            op, expr, dummy = sfct.groups()
            val_ms = safe_eval_expr(expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val_ms, int):
                results.append(f"固定詠唱時間 {sign}{val_ms / 1000:.2f} 秒")
            else:
                results.append(f"固定詠唱時間 {sign}({val_ms}) 秒（無法解析）")
            sfct_handled = True
            continue


        # 增減「指定技能傷害(裝備段)」合併處理
        register_function("AddDamage_SKID", "增加技能傷害(裝備段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_SKID", "減少技能傷害(裝備段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_sub_dmg_skid = re.match(r"(Add|Sub)Damage_SKID\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)\s*$", line)
        if add_sub_dmg_skid and condition_met:
            op, skill_id, value_expr = add_sub_dmg_skid.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            if isinstance(val, int):
                sign = "+" if op == "Add" else "-"
                results.append(f"技能【{skill_name}】傷害(裝備段) {sign}{val}%")
            else:
                sign = "+" if op == "Add" else "-"
                results.append(f"技能【{skill_name}】傷害(裝備段) {sign}({val})%（無法解析）")
            continue

            
        # 增減「指定技能傷害(技能段)」合併處理
        register_function("AddDamage_passive_SKID", "增加技能傷害(技能段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubDamage_passive_SKID", "減少技能傷害(技能段)", [
            {"name": "目標", "map": "unit_map"},
            {"name": "技能", "map": "skill_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_sub_dmg_passive = re.match(
            r"(Add|Sub)Damage_passive_SKID\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)\s*$",
            line
        )
        if add_sub_dmg_passive and condition_met:
            op, skill_id, value_expr = add_sub_dmg_passive.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val, int):
                results.append(f"技能【{skill_name}】傷害(技能段) {sign}{val}%")
            else:
                results.append(f"技能【{skill_name}】傷害(技能段) {sign}({val})%（無法解析）")
            continue

            
        # 指定技能冷卻時間（毫秒）增加/減少 合併處理
        skill_delay = re.match(r"(Add|Sub)SkillDelay\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if skill_delay and condition_met:
            op, skill_id, delay_expr = skill_delay.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val_ms = safe_eval_expr(delay_expr, variables, get_values, refine_inputs, grade)

            if isinstance(val_ms, int):
                delta = val_ms if op == "Add" else -val_ms
                skill_delay_accum[skill_name] = skill_delay_accum.get(skill_name, 0) + delta
            else:
                # 保留原本的無法解析提示
                results.append(f"技能【{skill_name}】冷卻時間變化 ({val_ms}) 毫秒（無法解析）")
            continue
            
        # 增減 變動詠唱時間（%）合併處理
        register_function("SubSpellCastTime", "減少變動詠唱時間", [{"name": "數值%", "type": "value"}])
        register_function("AddSpellCastTime", "增加變動詠唱時間", [{"name": "數值%", "type": "value"}])

        cast_time = re.match(r"(Add|Sub)SpellCastTime\(\s*(.+)\s*\)", line)
        if cast_time and condition_met:
            op, value_expr = cast_time.groups()
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            try:
                results.append(f"變動詠唱時間 {sign}{val}%")
            except Exception:
                results.append(f"變動詠唱時間 {sign}({value_expr})%（無法解析）")
            continue


        # Add/Sub SpecificSpellCastTime（指定技能變動詠唱時間 %）
        specific_cast = re.match(r"(Add|Sub)SpecificSpellCastTime\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if specific_cast and condition_met:
            op, skill_id, value_expr = specific_cast.groups()
            skill_name = skill_map.get(int(skill_id), f"技能ID {skill_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            if isinstance(val, int):
                results.append(f"技能【{skill_name}】變動詠唱時間 {sign}{val}%")
            else:
                results.append(f"技能【{skill_name}】變動詠唱時間 {sign}({val})%（無法解析）")
            continue
        # Add/Sub EXPPercent_KillRace (從擊殺魔物獲得的經驗%)
        exp_race = re.match(r"(Add|Sub)EXPPercent_KillRace\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if exp_race and condition_met:
            op, race_id, value_expr = exp_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"從 {race_name} 型怪的經驗值 {sign}{val}%")
            continue




#==========以上通用變數
#==========以下魔法判斷        
        # Add/Sub MDamage_Size（體型魔法）
        register_function("AddMDamage_Size", "增加體型魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMDamage_Size", "減少體型魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])

        mdamage_size = re.match(r"(Add|Sub)MDamage_Size\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if mdamage_size and condition_met:
            op, size_id, value_expr = mdamage_size.groups()
            size_name = size_map.get(int(size_id), f"尺寸{size_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {size_name} 敵人的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub SkillMDamage（屬性魔法傷害）
        register_function("AddSkillMDamage", "增加屬性魔法傷害", [
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubSkillMDamage", "減少屬性魔法傷害", [
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])

        skill_mdamage = re.match(r"(Add|Sub)SkillMDamage\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if skill_mdamage and condition_met:
            op, elem_id, value_expr = skill_mdamage.groups()
            element = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"{element} 的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub MDamage_Property（對指定種族與屬性）
        register_function("AddMDamage_Property", "增加屬性對象魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMDamage_Property", "減少屬性對象魔法傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])

        add_mdamage_prop = re.match(r"(Add|Sub)MDamage_Property\(\s*1\s*,\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if add_mdamage_prop and condition_met:
            op, elem_id, value_expr = add_mdamage_prop.groups()
            elem_name = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {elem_name} 對象的魔法傷害 {sign}{val}%")
            continue


        # Add/Sub Mdamage_Race（對種族魔法傷害）
        register_function("AddMdamage_Race", "增加種族魔法傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("SubMdamage_Race", "減少種族魔法傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])

        mdamage_race = re.match(r"(Add|Sub)Mdamage_Race\(\s*(\d+)\s*,\s*(.+)\s*\)", line)
        if mdamage_race and condition_met:
            op, race_id, value_expr = mdamage_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {race_name} 型怪的魔法傷害 {sign}{val}%")
            continue


        # AddMdamage_Class（對階級魔法傷害）
        
        register_function("AddMdamage_Class", "增加階級魔法傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])

        # AddMdamage_Class / SubMdamage_Class 合併處理
        mdamage_class = re.match(r"(Add|Sub)Mdamage_Class\(\s*(\d+)\s*,\s*(.+?)\s*\)", line)
        if mdamage_class and condition_met:
            op, class_id, value_expr = mdamage_class.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)

            sign = "+" if op == "Add" else "-"
            results.append(f"對 {class_name} 階級的魔法傷害 {sign}{val}%")
            continue

        # SetIgnoreMdefClass（無視階級魔防）
        
        register_function("SetIgnoreMdefClass", "無視階級魔法防禦", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mdef = re.match(r"SetIgnoreMdefClass\((\d+),\s*(.+?)\)", line)
        if ignore_mdef and condition_met:
            class_id, value_expr = ignore_mdef.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {class_name} 階級的魔法防禦 {val}%")
            continue

        # AddIgnore_MRES_RacePercent（無視種族魔抗）
        
        register_function("AddIgnore_MRES_RacePercent", "無視種族魔法抗性", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mres_race = re.match(r"AddIgnore_MRES_RacePercent\((\d+),\s*(.+?)\)", line)
        if ignore_mres_race and condition_met:
            race_id, value_expr = ignore_mres_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 的魔法抗性 {val}%")
            continue
            
        # SetIgnoreMdefClass（無視種族魔防）
        
        register_function("SetIgnoreMdefRace", "無視種族魔法防禦", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_mdef_race = re.match(r"SetIgnoreMdefRace\((\d+),\s*(.+?)\)", line)
        if ignore_mdef_race and condition_met:
            race_id, value_expr = ignore_mdef_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 的魔法防禦 {val}%")
            continue
            
            
            
            
#===========以上魔法判斷
#===========以下物理判斷

        #修煉ATK WeaponMasteryATK(value)
        MasteryATK_dmg = re.match(r"WeaponMasteryATK\(\s*(.+?)\)", line)
        if MasteryATK_dmg and condition_met:
            value_expr = MasteryATK_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"修煉ATK +{value_expr}")
            continue

        # AddMeleeAttackDamage(1, value)
        
        register_function("AddMeleeAttackDamage", "近距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        melee_dmg = re.match(r"AddMeleeAttackDamage\(\s*1\s*,\s*(.+)\)", line)
        if melee_dmg and condition_met:
            value_expr = melee_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"近距離物理傷害 +{value_expr}%")
            continue

        # AddRangeAttackDamage(1, value)
        
        register_function("AddRangeAttackDamage", "遠距離物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        range_dmg = re.match(r"AddRangeAttackDamage\(\s*1\s*,\s*(.+)\)", line)

        if range_dmg and condition_met:
            value_expr = range_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"遠距離物理傷害 +{value_expr}%")
            continue
            
        # AddBowAttackDamage(1, value)#弓攻擊力轉換遠傷。 實際上要裝備弓才能加進遠傷內。目前無判斷!
        range_dmg = re.match(r"AddBowAttackDamage\(\s*1\s*,\s*(.+)\)", line)
        
        if range_dmg and condition_met:
            value_expr = range_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"遠距離物理傷害 +{value_expr}%")
            continue

        # AddDamage_CRI(1, value)
        
        register_function("AddDamage_CRI", "爆擊傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        cri_dmg = re.match(r"AddDamage_CRI\(\s*1\s*,\s*(.+)\)", line)
        if cri_dmg and condition_met:
            value_expr = cri_dmg.group(1)
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"爆擊傷害 +{value_expr}%")
            continue


        # AddDamage_Size(1, size_id, value)
        
        register_function("AddDamage_Size", "增加體型物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "體型", "map": "size_map"},
            {"name": "數值%", "type": "value"}
        ])
        size_dmg = re.match(r"AddDamage_Size\(\s*1\s*,\s*(\d+),\s*(.+?)\)", line)
        if size_dmg and condition_met:
            
            size_id, value_expr = size_dmg.groups()
            size_str = size_map.get(int(size_id), f"體型{size_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"對 {size_str} 敵人的物理傷害 +{value_expr}%")
            continue

        # AddDamage_Property（對指定種族與屬性）
        
        register_function("AddDamage_Property", "增加屬性敵人物理傷害", [
            {"name": "目標", "map": "unit_map"},
            {"name": "屬性", "map": "element_map"},
            {"name": "數值%", "type": "value"}
        ])
        add_damage_prop = re.match(r"AddDamage_Property\(\s*1\s*,\s*(\d+),\s*(.+?)\)", line)
        if add_damage_prop and condition_met:
            elem_id, value_expr = add_damage_prop.groups()
            
            elem_name = element_map.get(int(elem_id), f"屬性{elem_id}")
            val = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"對 {elem_name} 對象的物理傷害 +{val}%")
            continue

        # SetIgnoreDEFRace(race_id)
        ignore_race = re.match(r"SetIgnoreDEFRace\((\d+)\)", line)
        if ignore_race and condition_met:
            race_name = race_map.get(int(ignore_race.group(1)), f"種族{ignore_race.group(1)}")
            results.append(f"無視 {race_name} 型怪的物理防禦")
            continue

        # SetIgnoreDefRace_Percent(race_id, value)
        
        register_function("SetIgnoreDefRace_Percent", "無視種族物理防禦", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_race_pct = re.match(r"SetIgnoreDefRace_Percent\((\d+),\s*(\d+)\)", line)
        if ignore_race_pct and condition_met:
            race_id, value = ignore_race_pct.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            results.append(f"無視 {race_name} 型怪的物理防禦 {value}%")
            continue

        # SetIgnoreDEFClass(class_id)
        ignore_class = re.match(r"SetIgnoreDEFClass\((\d+)\)", line)
        if ignore_class and condition_met:
            class_name = class_map.get(int(ignore_class.group(1)), f"階級{ignore_class.group(1)}")
            results.append(f"無視 {class_name} 階級的物理防禦")
            continue
            
        # PerfectDamage(1)
        perfect_damage = re.match(r"^PerfectDamage\(1\)$", line.strip())
        if perfect_damage and condition_met:
            results.append(f"武器體型修正 100%")
            continue

        # SetIgnoreDefClass_Percent(class_id, value)
        
        register_function("AddExtParam", "無視階級物理防禦", [
            {"name": "階級", "map": "class_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_class_pct = re.match(r"SetIgnoreDefClass_Percent\((\d+),\s*(\d+)\)", line)
        if ignore_class_pct and condition_met:
            class_id, value = ignore_class_pct.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            results.append(f"無視 {class_name} 階級的物理防禦 {value}%")
            continue

        # RaceAddDamage(race_id, value)
        
        register_function("RaceAddDamage", "增加種族物理傷害", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        race_dmg = re.match(r"RaceAddDamage\((\d+),\s*(.+?)\)", line)
        if race_dmg and condition_met:
            race_id, value_expr = race_dmg.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"對 {race_name} 型怪的物理傷害 +{value_expr}%")
            continue
                
        # AddIgnore_RES_RacePercent(race_id, value)
        
        register_function("AddIgnore_RES_RacePercent", "無視種族物理抗性", [
            {"name": "種族", "map": "race_map"},
            {"name": "數值%", "type": "value"}
        ])
        ignore_res_race = re.match(r"AddIgnore_RES_RacePercent\((\d+),\s*(.+?)\)", line)
        if ignore_res_race and condition_met:
            race_id, value_expr = ignore_res_race.groups()
            race_name = race_map.get(int(race_id), f"種族{race_id}")
            value_expr = safe_eval_expr(value_expr, variables, get_values, refine_inputs, grade)
            results.append(f"無視 {race_name} 的物理抗性 {value_expr}%")
            continue
            
        # 階級物理傷害加成：ClassAddDamage(1, class_id, value)

        register_function("ClassAddDamage", "增加階級的物理傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        register_function("ClassSubDamage", "減少階級的物理傷害", [
            {"name": "階級", "map": "class_map"},
            {"name": "目標", "map": "unit_map"},
            {"name": "數值%", "type": "value"}
        ])
        class_dmg = re.match(r"Class(Add|Sub)Damage\(\s*(\d+)\s*,\s*1\s*,\s*(.+?)\s*\)", line)
        if class_dmg and condition_met:
            op, class_id, expr_src = class_dmg.groups()
            class_name = class_map.get(int(class_id), f"階級{class_id}")
            val = safe_eval_expr(expr_src, variables, get_values, refine_inputs, grade)
            sign = "+" if op == "Add" else "-"
            results.append(f"對 {class_name} 階級的物理傷害 {sign}{val}%")
            continue

            

#==============以上物理判斷

#待處理判斷
#通用(恢復效果、誘導攻擊、SP消耗
#自身(對某種族減傷、對某種族抗性、
#物理(物理反射%、對屬性減少傷害、對某種族的CRI+% 弓攻擊力轉換成遠傷(實際要裝備弓才能算進遠傷)
#魔法(魔法反射
#================以下判斷失敗或不成立區塊
        if not hide_unrecognized:
            stripped = original_line.strip()
            if stripped and not stripped.startswith("--"):  # 排除空白行和註解
                if not condition_met:
                    results.append(f"⛔ 已跳過（條件不成立）: {original_line}")
                else:
                    results.append(f"🟡line解析 無法辨識: {original_line}")






    for skill_name, total_ms in skill_delay_accum.items():
        sec = abs(total_ms) / 1000
        if total_ms < 0:
            results.append(f"技能【{skill_name}】冷卻時間縮短 {sec:.2f} 秒")
        else:
            results.append(f"技能【{skill_name}】冷卻時間延長 {sec:.2f} 秒")







            
        # 所有邏輯都未匹配時：顯示無法辨識語句


    





    def combine_effects(results):
        combined = defaultdict(int)
        final_lines = []
        
        for line in results:
            # 支援加總格式：「效果說明 +數值」或「效果說明 -數值」
            match = re.match(r"(.+?) ([+-]\d+)([%]?)$", line)
            if match:
                key = match.group(1).strip()
                value = int(match.group(2))
                suffix = match.group(3)  # % 結尾
                combined[(key, suffix)] += value
            else:
                final_lines.append(line)

        for (key, suffix), total in combined.items():
            final_lines.append(f"{key} {total:+d}{suffix}")

        return final_lines

        results.append(f"🟡 無法辨識: {original_line}")

   
    if hide_unrecognized:
        return combine_effects(results)
        
    else:
        return results

def convert_description_to_html(description_lines):#視覺化說明欄
    html_lines = []
    color_stack = []

    for line in description_lines:
        result = ""
        i = 0
        while i < len(line):
            if line[i] == "^" and i + 6 < len(line):
                color_code = line[i+1:i+7]
                if re.fullmatch(r"[0-9a-fA-F]{6}", color_code):
                    result += f'<span style="color:#{color_code}">'
                    color_stack.append("</span>")
                    i += 7
                    continue
            result += line[i]
            i += 1

        # 關閉所有尚未關閉的 <span>
        while color_stack:
            result += color_stack.pop()
        html_lines.append(result)

    return "<br>".join(html_lines)

def decompile_lub(lub_path, output_path="iteminfo_new.lua"):#反編譯iteminfo_new
    if not os.path.exists(lub_path):
        QMessageBox.critical(None, "錯誤", f"找不到 LUB 檔案：\n{lub_path}")
        return False

    try:
        with open(output_path, "w", encoding="utf-8") as out_file:
            subprocess.run(
                [r"APP\luadec.exe", lub_path],
                stdout=out_file,
                stderr=subprocess.PIPE,
                check=True
            )
        return True
    except subprocess.CalledProcessError as e:
        QMessageBox.critical(None, "反編譯失敗", e.stderr.decode("utf-8", errors="ignore"))
        return False
    except FileNotFoundError:
        QMessageBox.critical(None, "錯誤", "找不到 luadec.exe，請確認它放在data資料夾。")
        return False

def parse_lub_file(filename):#字典化物品列表


    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        QMessageBox.critical(None, "錯誤", f"找不到檔案：{filename}")
        return {}

    item_entries = re.findall(r"\[(\d+)\]\s*=\s*{(.*?)}\s*,\s*(?=\[|\})", content, re.DOTALL)
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

#素質點計算#取自ROCalculator
def calculate_stat_points(level: int, transcendent: bool = False) -> int:
    pt = 100 if transcendent else 100 - 52
    for i in range(1, level):
        if i < 100:
            pt += i // 5 + 3
        elif i <= 150:
            pt += i // 10 + 13
        elif i <= 185:
            pt += 28 + (i - 150) // 7
        elif i < 200:
            pt += 33 + (i - 185) // 7
    return pt
#素質消耗計算#取自ROCalculator
def raising_stats(stat_str: str) -> int:
    try:
        val = int(stat_str.split('+')[0])
    except Exception:
        return 0

    pt = 0
    for i in range(1, val):
        if i < 100:
            pt += (i - 1) // 10 + 2
        else:
            pt += 4 * ((i - 100) // 5) + 16
    return pt


class ItemSearchApp(QWidget):
    
    def update_window_title(self):
        filename = os.path.basename(self.current_file) if self.current_file else "未命名"
        self.setWindowTitle(f"RO物品查詢計算工具 - {filename}")
    
    def replace_custom_calc_content(self):
        # 特殊 CheckBox 狀態
        special_state = "|".join(
            f"{key}:{checkbox.isChecked()}"
            for key, checkbox in self.special_checkboxes.items()
        )
        current_text = self.custom_calc_box.toPlainText()
        skill_key = self.skill_box.currentData()
        skill_lv = self.skill_LV_input.text()
        
        # ✅ 裝備狀態（你可以根據實際來源換成 combo_effect_text.text() 之類的）
        equip_state = self.total_effect_text.toPlainText()
        # 目標設定選項
        size_key = self.size_box.currentData()
        element_key = self.element_box.currentData()
        race_key = self.race_box.currentData()
        class_key = self.class_box.currentData()
        element_lv_key = self.element_lv_input.text() or 1
        user_element_key = self.attack_element_box.currentData()
        monsterDamage_key = self.monsterDamage_input.text() or "0"
        # 整數輸入值（注意空字串要預設為 0）
        d_ef = self.def_input.text() or "0"
        defc = self.defc_input.text() or "0"
        res = self.res_input.text() or "0"
        mdef = self.mdef_input.text() or "0"
        mdefc = self.mdefc_input.text() or "0"
        mres = self.mres_input.text() or "0"
        # 組合新的 state_key
        state_key = f"{skill_key}|{skill_lv}|{current_text}|{equip_state}|{special_state}|{size_key}|{element_key}|{race_key}|{class_key}|{d_ef}|{defc}|{res}|{mdef}|{mdefc}|{mres}|{element_lv_key}|{user_element_key}|{monsterDamage_key}"


        if getattr(self, "_last_calc_state", None) == state_key:
            print("【⛔ 裝備效果沒有更動，跳過運算。】")
            return  # ⛔ 跳過重複運算

        self._last_calc_state = state_key  # ✅ 更新狀態紀錄

        print("【🧠 執行 replace_custom_calc_content()】")
        # 原本你的公式解析邏輯
                #轉成全域變數
        def get_effect_multiplier(category, index):
            return getattr(self, f"{category}_{index}", 0)
        
        result = []
        stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK",
                      "POW", "STA", "WIS", "SPL", "CON", "CRT"]

        # === 從 UI 中取 BaseLv 與 JobLv ===
        try:
            base_lv = int(self.input_fields["BaseLv"].text())
        except:
            base_lv = 0

        try:
            job_lv = int(self.input_fields["JobLv"].text())
        except:
            job_lv = 0

        globals()["BaseLv"] = base_lv
        globals()["JobLv"] = job_lv

        # === 從 UI 輸入 + 職業 + 裝備效果取各項能力加成 ===
        job_id = self.input_fields["JOB"].currentData()
        job_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
        raw_effects = getattr(self, "effect_dict_raw", {})

        for i, stat in enumerate(stat_names):
            try:
                base = int(self.input_fields[stat].text())
            except:
                base = 0
            job = job_bonus[i] if i < len(job_bonus) else 0
            equip = sum(val for val, _ in raw_effects.get((stat, ""), []))
            total = base + job + equip

            # 🔧 自動產生變數：base_STR, job_STR, equip_STR, total_STR
            globals()[f"base_{stat}"] = base
            globals()[f"job_{stat}"] = job
            globals()[f"equip_{stat}"] = equip
            globals()[f"total_{stat}"] = total

        #======================取所有增傷資料到變數區=====================
        effect_dict = getattr(self, "effect_dict_raw", {})
        #呼叫處理物理,魔法增傷,無視防禦 例:(對"小型"敵人的魔法傷害 +5%)
        self.apply_all_damage_effects(effect_dict)
        #武器類型(數字)
        weapon_class = global_weapon_type_map.get(4, 0)
        #武器類型(代號)
        globals()["weapon_codes"] = weapon_class_codes.get(weapon_class, "?")

        #裝備ATK(不含武器)
        globals()["ATK_armor"] = sum(val for val, _ in effect_dict.get(("ATK", ""), []))
        #修煉ATK
        WeaponMasteryATK = sum(val for val, _ in effect_dict.get(("修煉ATK", ""), []))
        #裝備MATK(不含武器)
        globals()["MATK_armor"] = sum(val for val, _ in effect_dict.get(("MATK", ""), []))
        #裝備ATK%
        globals()["ATK_percent"] = sum(val for val, _ in effect_dict.get(("ATK%", "%"), []))
        #裝備MATK%
        globals()["MATK_percent"] = sum(val for val, _ in effect_dict.get(("MATK%", "%"), []))
        #武器ATK
        globals()["ATK_Mweapon"] = sum(val for val, _ in effect_dict.get(("武器ATK", ""), []))
        #武器MATK
        globals()["MATK_Mweapon"] = sum(val for val, _ in effect_dict.get(("武器MATK", ""), []))
        #武器等級
        globals()["weapon_Level"] = sum(val for val, _ in effect_dict.get(("武器等級", ""), []))
        #箭矢彈藥ATK
        globals()["ammoATK"] = sum(val for val, _ in effect_dict.get(("箭矢/彈藥ATK", ""), []))
        #武器精煉R右L左
        globals()["weaponRefineR"] = int(self.refine_inputs_ui["右手(武器)"]["refine"].text())
        weaponRefineL = int(self.refine_inputs_ui["左手(盾牌)"]["refine"].text())
        #武器階級R右L左
        globals()["weaponGradeR"] = int(self.refine_inputs_ui["右手(武器)"]["grade"].currentIndex())
        weaponGradeL = int(self.refine_inputs_ui["左手(盾牌)"]["grade"].currentIndex())
        #print(f"{weaponRefineR} {weaponRefineL} {weaponGradeR} {weaponGradeL}")
        globals()["PATK"] = sum(val for val, _ in effect_dict.get(("P.ATK", ""), []))
        globals()["SMATK"] = sum(val for val, _ in effect_dict.get(("S.MATK", ""), []))
        #print(f"S.MATK{SMATK}")
        #公式用
        SKILL_HW_MAGICPOWER = sum(val for val, _ in effect_dict.get(("可使用【魔力增幅】Lv.", ""), []))        
        SKILL_ASC_KATAR = (sum(val for val, _ in effect_dict.get(("可使用【高階拳刃修練】Lv.", ""), [])) * 2) + 10 if weapon_class == 16 else 0
        #print(f"高階拳刃修煉 {SKILL_ASC_KATAR}")
        #print(f"魔力增幅 {SKILL_HW_MAGICPOWER}")


        # 從下拉選單與欄位取得目標資訊
        target_size    = self.size_box.currentData()
        target_element = self.element_box.currentData()
        target_race    = self.race_box.currentData()
        target_class   = self.class_box.currentData()
        User_attack_element = self.attack_element_box.currentData()

        #輸出ROCalculator全域變數區 globals()[""] = 
        globals()["RaceMatkPercent"] = get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999)#魔法種族
        globals()["SizeMatkPercent"] = get_effect_multiplier('MD_size', target_size)#魔法體型
        globals()["LevelMatkPercent"] = get_effect_multiplier('MD_class', target_class)#魔法階級
        globals()["ElementalMatkPercent"] = get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10)#魔法屬性敵人
        globals()["ElementalMagicPercent"] = get_effect_multiplier('MD_Damage', User_attack_element) + get_effect_multiplier('MD_Damage', 10)#屬性魔法
        globals()["RaceAtkPercent"] = get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999)#物理種族
        globals()["SizeAtkPercent"] = get_effect_multiplier('D_size', target_size)#物理體型
        globals()["LevelAtkPercent"] = get_effect_multiplier('D_class', target_class)#物理階級
        globals()["ElementalAtkPercent"] = get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10)#物理屬性敵人
        

        
        
        skill_hits = int(self.skill_hits_input.text())#攻擊次數
        #print(f"打擊次數 {skill_hits}")
        try:
            target_element_lv = int(self.element_lv_input.text() or 1)#目標屬性等級
        except ValueError:
            target_element_lv = 1
        #print(f"目標屬性等級:{target_element_lv}")
        try:
            target_monsterDamage = int(self.monsterDamage_input.text() or 0)
        except ValueError:
            target_monsterDamage = 0
        try:
            target_def = int(self.def_input.text() or 0)
        except ValueError:
            target_def = 0
        try:
            target_defc = int(self.defc_input.text() or 0)
        except ValueError:
            target_defc = 0
        try:
            target_res = int(self.res_input.text() or 0)
        except ValueError:
            target_res = 0
        try:
            target_mdef = int(self.mdef_input.text() or 0)
        except ValueError:
            target_mdef = 0
        try:
            target_mdefc = int(self.mdefc_input.text() or 0)
        except ValueError:
            target_mdefc = 0
        try:
            target_mres = int(self.mres_input.text() or 0)
        except ValueError:
            target_mres = 0


        #=================== 特殊增傷ui取得/處理區===================
        #萬紫4
        skill_wanzih4_buff = 100 if self.special_checkboxes["wanzih_checkbox"].isChecked() and User_attack_element == 3 else 0
        #魔力中毒
        magic_poison_buff = 50 if self.special_checkboxes["magic_poison_checkbox"].isChecked() else 0
        #屬性紋章
        attribute_seal_buff = 50 if self.special_checkboxes["attribute_seal_checkbox"].isChecked() and 1 <= User_attack_element <= 4 else 0
        #潛擊
        is_sneak_checked = self.special_checkboxes["sneak_attack_checkbox"].isChecked()
        sneak_attack_buff = 30 if is_sneak_checked and target_class == 0 else 15 if is_sneak_checked else 0



        
        """
        target_size       # 來自 體型 的數值
        C    # 屬性編號
        target_element_lv # 目標屬性等級
        target_race       # 種族代碼C
        target_class      # 階級代碼
        target_mdef       # 數字輸入 MDEF前
        target_mdefc      # 數字輸入 MDEF後
        target_mres       # 數字輸入 MRES
        User_attack_element #施展屬性
        skill_hits_input
        """
        #=============參考動態變數自動抓技能%=(裝備段)==============
        # 從 skill_box 取得目前選中的技能名稱（顯示文字）
        selected_skill_name = self.skill_box.currentText()
        globals()["Use_Skills"] = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】傷害(裝備段)", "%"), []))
        #=============參考動態變數自動抓技能%=(技能段)==============      
        passive_skill_buff = sum(val for val, _ in effect_dict.get((f"技能【{selected_skill_name}】傷害(技能段)", "%"), []))
        #=====================其他物理增傷========================
        globals()["MeleeAttackDamage"] = sum(val for val, _ in effect_dict.get((f"近距離物理傷害", "%"), []))
        globals()["RangeAttackDamage"] = sum(val for val, _ in effect_dict.get((f"遠距離物理傷害", "%"), []))
        globals()["Damage_CRI"] = sum(val for val, _ in effect_dict.get((f"爆擊傷害", "%"), []))
        globals()["CRATE"] = sum(val for val, _ in effect_dict.get((f"C.RATE", ""), []))   
        Ignore_size = sum(val for val, _ in effect_dict.get((f"武器體型修正", "%"), []))   
        

        


        #========================以上魔法增傷===================
        



        #=======取得目前有的技能等級如果沒有回傳0        
        def GSklv(skill_id):
            return enabled_skill_levels.get(skill_id, 0)  # 若沒有這個技能，預設回傳 0
        #處理公式中的動態變數
        def replace_gsklv_calls(formula: str) -> str:
            pattern = r'GSklv\((\d+)\)'  # 找出 GSklv(數字)
            return re.sub(pattern, lambda m: str(GSklv(int(m.group(1)))), formula)
        def replace_custom_calls(formula):#例如超自然波 書跟杖打擊次數
            # ✅ 處理 WPon(x|y|...)a:b 武器類型條件分支
            def replace_wpon_expr(match):
                global global_weapon_type_map  # 正確引用全域變數
                types_str = match.group(1)
                if_true = match.group(2)
                if_false = match.group(3)

                target_types = set(int(x) for x in types_str.split("|"))
                weapon_class = global_weapon_type_map.get(4, 0)#只看主手

                return if_true if weapon_class in target_types else if_false

            return re.sub(
                r'WPon\(([\d|]+)\)([^:]+):([^:\)\s\+\-\*/]+)',
                replace_wpon_expr,
                formula
            )



        #=======================技能欄公式====================
        #====================MRES,MDEF計算===================
        #====================MDEF計算==================
        def calc_final_mdef_damage(mdef: float, reduction_percent: float) -> float:
            """
            根據 Excel 公式計算最終魔法傷害比例
            mdef: 後 MDEF 數值
            reduction_percent: MDEF 破防百分比（例如 64 表示 64%）
            回傳: 傷害倍率（小數，例如 0.4222）
            """
            
            reduction = reduction_percent / 100
            if reduction > 0.99:
                return 1.0
            adj = mdef - (mdef * reduction) - reduction
            numerator = 1000 + adj
            denominator = 1000 + adj * 10
            resistance = numerator / denominator
            return min(resistance, 1.0)  # ⬅️ 保證不超過 1.0
        #====================MRES計算==================
        def calc_final_mres_damage(mres: float, reduction_percent: float) -> float:

            reduction = reduction_percent / 100
            if reduction > 0.99:
                return 1.0
            adj = mres - (mres * reduction) - reduction
            numerator = 2000 + adj
            denominator = 2000 + adj * 5
            resistance = numerator / denominator
            return min(resistance, 1.0)  # ⬅️ 保證不超過 1.0
            
        #魔法破防
        #mdef m33=破防 l37=敵人mdef
        #=IF(M33>0.99,1,(1000+(L37-(L37*M33)-M33))/(1000+(L37-(L37*M33)-M33)*10))
        mdef_reduction = ((get_effect_multiplier('MD_Race_def', target_race))+(get_effect_multiplier('MD_class_def', target_class)))
        Mdamage_nomdef = calc_final_mdef_damage(target_mdef, mdef_reduction)
        #print(f"最終傷害比例：{Mdamage_nomdef:.4f} → {Mdamage_nomdef * 100:.2f}%")

        
        #mres
        #=IF(M34>0.99,1,(2000+(L39-(L39*M34)-M34))/(2000+(L39-(L39*M34)-M34)*5))
        mres_reduction = ((get_effect_multiplier('MD_Race_res', target_race))+(get_effect_multiplier('MD_Race_res', 9999)))
        mres_reduction = min(mres_reduction, 50)#破抗性最大50%
        Mdamage_nomres = calc_final_mres_damage(target_mres, mres_reduction)
        #print(f"抗性最終傷害比例：{Mdamage_nomres:.4f} → {Mdamage_nomres * 100:.2f}%")

        

        
        #result.append(f"體型編號: {target_size}")
        #result.append(f"屬性編號: {target_element}")
        #result.append(f"種族編號: {target_race}")
        #result.append(f"階級編號: {target_class}")
        #result.append(f"施展屬性: {User_attack_element}")
        
        # 查詢屬性倍率函數
        def get_damage_multiplier(attacker_element: int, defender_element: int, level: int) -> int:
            if level not in damage_tables:
                raise ValueError("不支援的屬性等級（僅支援 Lv1~Lv4）")
            if attacker_element not in element_map or defender_element not in element_map:
                raise ValueError("屬性 ID 必須在 0~9 範圍內")

            return damage_tables[level][attacker_element][defender_element]

        
        # 武器體型懲罰(物理)
        def get_size_penalty(weapon_class: int, target_size: int) -> float:
            """根據武器類型與目標體型回傳懲罰倍率（小數，例如 1.0, 0.75）"""
            penalties = weapon_type_size_penalty.get(weapon_class, [100, 100, 100])
            if 0 <= target_size < len(penalties):
                return penalties[target_size] / 100.0
            return 1.0  # 預設值 100% → 1.0



        #==========================精煉計算=========================
        #武器ATK精煉計算
        patk_refine_total = 0
        atk_refine_total, patk_refine_total = self.calc_weapon_refine_atk(weapon_Level, weaponRefineR, weaponGradeR)
        #PATK(裝備+精煉+特性素質)
        patk_total = PATK + int(total_POW/3) + int(total_CON/5) + patk_refine_total
        #武器MATK精煉計算
        smatk_refine_total = 0
        matk_refine_total, smatk_refine_total = self.calc_weapon_refine_matk(weapon_Level, weaponRefineR, weaponGradeR)
        #print(f"精煉加成 MATK: {matk_refine_total}")
        #print(f"精煉加成 S.MATK: {smatk_refine_total}")
        #============================魔法各增傷計算區============================
        #SMATK(裝備+精煉+特性素質)
        SMATK_total = SMATK + int(total_SPL/3) + int(total_CON/5) + smatk_refine_total
        
        
        def apply_stepwise_percent_mode(base, *bonuses_with_mode):
            """
            擴充版，每層乘完取整，依據 mode 控制加/減/忽略：
            - mode = 1      → 加成百分比：乘 (1 + bonus / 100)
            - mode = 1.4    → 特殊加成百分比：乘 (1.4 + bonus / 100)
            - mode = 0      → 原始倍率：乘 (bonus / 100)
            - mode = -1     → 減傷百分比：乘 (1 - bonus / 100)
            - mode = None   → 固定扣值：value -= bonus
            - mode = "raw"  → 直接乘：value *= bonus（不除以 100）
            - mode = "+"    → 直接加：value += bonus
            """
            value = base
            for bonus, mode in bonuses_with_mode:
                if mode is None:
                    value -= bonus
                elif mode == "raw":
                    value *= bonus
                elif mode == "+":
                    value += bonus
                else:
                    if mode == 1:
                        multiplier = 1 + bonus / 100
                    elif mode == 1.4:
                        multiplier = 1.4 + bonus / 100
                    elif mode == -1:
                        multiplier = 1 - bonus / 100
                    elif mode == 0:
                        multiplier = bonus / 100
                          
                    else:  # mode == 0
                        multiplier = bonus / 100
                    value = int(value * multiplier)
                print(f"計算: {value}")
            return value

            

                
        def visual_length(s: str) -> int:
            """計算視覺寬度：全形字算2，半形算1"""
            width = 0
            for c in s:
                width += 2 if ord(c) > 255 else 1
            return width

        def pad_label(label: str, total_width: int = 20) -> str:
            """依據視覺寬度補空格，讓冒號後對齊"""
            space_count = total_width - visual_length(label)
            return label + " " * max(space_count, 0)
        

        #物理===================        
        #近傷ATK
        #NATK = int(BaseLv/4) + int(total_STR) + int(total_DEX/5) + int(total_LUK/3) + int(total_POW*5)
        NATK = int((BaseLv/4) + (total_STR) + (total_DEX/5) + (total_LUK/3) + (total_POW*5))
        #遠傷ATK(弓槍樂器鞭子)
        #FATK = int(BaseLv/4) + int(total_STR/5) + int(total_DEX) + int(total_LUK/3) + int(total_POW*5)
        FATK = int((BaseLv/4) + (total_STR/5) + (total_DEX) + (total_LUK/3) + (total_POW*5))
        #後ATK (只給面板顯示不參與計算)
        AKTC = ATK_Mweapon + ATK_armor + atk_refine_total
        #C.RATE
        total_CRATE = CRATE + int(total_CRT/3)   
        print(f"weapon_Level:{weapon_Level}")      
        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
            #武器基礎ATK(dex)
            BasicsWeaponATK = ATK_Mweapon * (1+ (total_DEX/200) + (weapon_Level*0.05))
            
        else:#STR系
            #武器基礎ATK(STR)
            BasicsWeaponATK = ATK_Mweapon * (1+ (total_STR/200) + (weapon_Level*0.05))
        
        print(f"BasicsWeaponATK:{BasicsWeaponATK}")
        #精煉武器ATK
        refineWeaponATK = int(BasicsWeaponATK + atk_refine_total)       
        print(f"refineWeaponATK:{refineWeaponATK}")        
        #武器體型修正
        Weaponpunish = 1 if Ignore_size == 100 else get_size_penalty(weapon_class, target_size)
            
        print(f"Ignore_size:{Ignore_size}") 
        print(f"武器體型修正:{Weaponpunish}")   
        #(精煉武器ATK*體型懲罰)+箭矢彈藥ATK
        refineammoATK = int(refineWeaponATK * Weaponpunish) + ammoATK
        
        #前素質總ATK
        
        
        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
            #ATKF = int((FATK*2) * (get_damage_multiplier(User_attack_element, target_element, target_element_lv)/100))
            ATKF = int((FATK*2) * (get_damage_multiplier(0, target_element, target_element_lv)/100)) #前段強制無屬 除非溫暖風轉屬
        else:#STR系
            ATKF = int((NATK*2) * (get_damage_multiplier(0, target_element, target_element_lv)/100)) #前段強制無屬 除非溫暖風轉屬
        
        #後武器總ATK
        ATKC_Mweapon_ALL = (refineammoATK + ATK_armor) 
        print(f"ATKC_Mweapon_ALL:{ATKC_Mweapon_ALL}")
        
        
        
        
        
        
        #魔法===================
        #前MATK
        MATKF = int(BaseLv/4) + int(total_INT*1.5) + int(total_DEX/5) + int(total_LUK/3) + int(total_SPL*5)
        #後MATK
        MATKC = MATK_armor + MATK_Mweapon + matk_refine_total
        #武器MATK
        MATK_Mweapon_ALL = MATKF + ((matk_refine_total + MATK_Mweapon) * (1+(weapon_Level*0.1)))
        #print(f"武器MATK:{MATK_Mweapon_ALL}")
        #裝備MATK+魔力增幅+武器MATK
        armorMATK_MAGICPOWER = int(MATK_Mweapon_ALL * (1+(SKILL_HW_MAGICPOWER*0.05)) + MATK_armor)
        #print(f"裝備MATK+魔力增幅:{armorMATK_MAGICPOWER}")
        
        
        #======================取得技能欄公式======================    
        # === 取得技能等級輸入並設為全域
        text = self.skill_LV_input.text()
        globals()["Sklv"] = int(text) if text.lstrip('-').isdigit() else 0
        
        # === 取得使用者從 UI 下拉選單選擇的技能名稱
        #selected_skill_name = self.skill_box.currentText()#上面已經做過了

        # === [1] 取得技能 row
        skill_row = skill_df[skill_df["Name"] == selected_skill_name]
        if skill_row.empty:
            raise ValueError(f"找不到技能：{selected_skill_name}")
        skill_row = skill_row.iloc[0]

        # [2] 根據種族選擇正確的公式，並同步 UI
        default_formula = str(skill_row["Calculation"]).strip()
        final_formula = default_formula

        if pd.notna(skill_row.get("Special_Calculation")) and pd.notna(skill_row.get("monster_race")):
            #print(f"[DEBUG]比對的的種族: {skill_row.get('monster_race')}")
            allowed_races = set(r.strip() for r in skill_row["monster_race"].split(","))
            #print(f"[DEBUG]輸入的種族: {target_race}")
            if str(target_race).strip() in allowed_races:
                final_formula = str(skill_row["Special_Calculation"]).strip()
                #print("[DEBUG]觸發更改技能欄為 Special_Calculation")

        # 同步更新 UI
        #self.skill_formula_input.setText(final_formula)

        # [3] 最終使用使用者輸入（如果手動改了）
        user_input_formula = self.skill_formula_input.text().strip()
        if user_input_formula and user_input_formula != final_formula:
            formula_str = user_input_formula
        else:
            formula_str = final_formula

        def parse_hits(value, sklv):
            """
            解析 hits 或 combo_hits 欄位，支援負數與公式。
            範例： (Sklv/3)+4 會以整數除法處理為 (Sklv // 3) + 4
            """
            try:
                # 若為 int 或 float，直接轉
                if isinstance(value, (int, float)):
                    return int(value)

                # 去除空白後判斷是否為整數字串（包含負數）
                stripped = str(value).strip()
                if stripped.lstrip("-").isdigit():
                    return int(stripped)

                # 將 '/' 換成 '//' 確保整數除法
                safe_expr = stripped.replace("/", "//")

                # 建立 Symbol 並解析表達式
                Sklv = Symbol("Sklv")
                expr = sympify(safe_expr)
                result = expr.evalf(subs={Sklv: sklv}, chop=True)  # chop=True 可去除浮點誤差

                return int(result)
            except Exception as e:
                print(f"[⚠️ hits 解析錯誤] 原始值: {value}, 錯誤: {e}")
                return 1  # 預設安全值


        # === [4] 主段傷害計算（含多段與 bonus 加值設定）
        repeat_count = self.skill_hits_input.text()
        bonus_add = float(skill_row["bonus_add"]) if pd.notna(skill_row.get("bonus_add")) else 0
        bonus_step = float(skill_row["bonus_step"]) if pd.notna(skill_row.get("bonus_step")) else 0
        decay_hits = int(skill_row["decay_hits"]) if pd.notna(skill_row.get("decay_hits")) else 0  # ✅ 補這段
        combo_element = int(skill_row["combo_elementg"]) if pd.notna(skill_row.get("combo_elementg")) else 0
        attack_type = str(skill_row.get("attack_type", "")).lower() if pd.notna(skill_row.get("attack_type")) else "physical"
        #技能爆傷判斷
        Critical_hit = float(skill_row["Critical_hit"]) if pd.notna(skill_row.get("Critical_hit")) else 1

        print(f"攻擊模式：{attack_type}")
        

        
        bottom_result = []
        def compute_and_record_damage(formula, repeat_count=1, bonus_add=0, bonus_step=0, label="main", skill_hits=1, user_attack_element=0):
            
            results = []
            allowed_vars = {k: v for k, v in globals().items() if isinstance(v, (int, float))}
            symbols_dict = {k: Symbol(k) for k in allowed_vars}

            for i in range(repeat_count):
                added_value = bonus_add + i * bonus_step
                full_formula = f"({formula}) + {added_value}" if added_value else formula
                full_formula = replace_gsklv_calls(full_formula)
                full_formula = replace_custom_calls(full_formula)
                print(f"轉換後的公式：{full_formula}")
                bottom_result.append(f"{pad_label('技能公式:')}[{i+1}/{repeat_count}] {full_formula}")

                try:
                    expr = sympify(full_formula, locals=symbols_dict)
                    used_symbols = {str(s) for s in expr.free_symbols}
                    missing_symbols = used_symbols - set(allowed_vars.keys())
                    if missing_symbols:
                        raise ValueError(f"公式中錯誤的符號： {missing_symbols}")

                    calc_result = expr.evalf(subs=allowed_vars)
                    #skill_result = round(calc_result, 2)
                    skill_result = int(calc_result)
                    print(f"[{i+1}/{repeat_count}] 技能公式結果: {skill_result}")
                    
                    if attack_type == "magic":
                        final_damage = apply_stepwise_percent_mode(
                            #初始值
                            armorMATK_MAGICPOWER,
                            #MATK%
                            (MATK_percent,1),
                            #體型
                            (get_effect_multiplier('MD_size', target_size),1),
                            #屬性敵人
                            (get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10),1),
                            #敵人屬性耐性
                            ((skill_wanzih4_buff + magic_poison_buff),1),
                            #屬性魔法
                            (get_effect_multiplier('MD_Damage', User_attack_element) +get_effect_multiplier('MD_Damage', 10),1),
                            #種族
                            (get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999),1),
                            #階級
                            (get_effect_multiplier('MD_class', target_class),1),
                            #特定魔物增傷
                            (target_monsterDamage,1),
                            #smatk 
                            (SMATK_total,1),
                            #技能倍率
                            (skill_result,0),
                            #屬性倍率
                            (get_damage_multiplier(User_attack_element, target_element, target_element_lv),0),
                            #敵人MRES減傷
                            (Mdamage_nomres,"raw"),
                            #敵人MDEF減傷
                            (Mdamage_nomdef,"raw"),
                            #敵人MDEF減算
                            (target_mdefc,None),
                            #裝備段技能增傷
                            (Use_Skills,1),
                            #技能段技能增傷
                            (passive_skill_buff,1),
                            #念力?
                            #潛擊 自動判斷階級
                            (sneak_attack_buff,1),
                            #屬性紋章 風水火地
                            (attribute_seal_buff,1),
                        )
                    elif attack_type == "physical":
                        #先計算ATK%已利後續計算
                        ATK_percent_sign = int(ATKC_Mweapon_ALL * (ATK_percent/100))
                        final_damage_1 = apply_stepwise_percent_mode(
                            #初始值 後武器ATK
                            ATKC_Mweapon_ALL,                            
                            #種族
                            (get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999),1),
                            #體型
                            (get_effect_multiplier('D_size', target_size),1),
                            #屬性敵人
                            (get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10),1),
                            #階級
                            (get_effect_multiplier('D_class', target_class),1),
                        )
                        
                        #後總ATK
                        final_damage_1 += ATK_percent_sign 
                        print(f"屬性倍率計算前: {final_damage_1}")
                        #屬性倍率
                        final_damage_1 = math.ceil(final_damage_1 * get_damage_multiplier(User_attack_element, target_element, target_element_lv) / 100)
                        print(f"屬性倍率計算後: {final_damage_1}")
                        #最終ATK
                        final_damage_1 += ATKF
                        print(f"最終ATK: {final_damage_1}")
                        #爆傷+技能半爆判斷
                        CRI_Critical_hit = (Damage_CRI * Critical_hit)
                        if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
                            final_damage = apply_stepwise_percent_mode(
                                #最終ATK初始值
                                final_damage_1,
                                #P.ATK
                                (patk_total,1),
                                #爆傷
                                (CRI_Critical_hit,1),
                                #遠傷%
                                (RangeAttackDamage,1),
                                #技能倍率
                                (skill_result,0),
                                #敵人DEF減算
                                (target_defc,None),
                                #裝備段技能增傷
                                (Use_Skills,1),
                                #技能段技能增傷
                                (passive_skill_buff,1),
                                #C.RATE
                                (total_CRATE,1.4),
                            )
                            print(f"技能爆擊最終傷害: {final_damage}")
                        else:#STR系
                            final_damage = apply_stepwise_percent_mode(
                                #最終ATK初始值
                                final_damage_1,
                                #P.ATK
                                (patk_total,1),
                                #武器修煉ATK
                                (WeaponMasteryATK,"+"),
                                #爆傷
                                (CRI_Critical_hit,1),
                                #近傷%
                                (MeleeAttackDamage,1),
                                #技能倍率
                                (skill_result,0),
                                #高階拳刃修煉
                                (SKILL_ASC_KATAR,1),
                                #敵人DEF減算
                                (target_defc,None),
                                #裝備段技能增傷
                                (Use_Skills,1),
                                #技能段技能增傷
                                (passive_skill_buff,1),
                                #C.RATE
                                (total_CRATE,1.4),
                            )
                            print(f"技能爆擊最終傷害: {final_damage}")
                        
                    else:
                        raise ValueError(f"未知的攻擊類型: {attack_type}")
                        
                    

                    if skill_hits < 0:# skill_hits < 0 表示這段總傷害要「均分」為多次
                        times = abs(skill_hits)
                        damage_by_hit = int(final_damage / times)
                        total_damage = damage_by_hit * times
                    else:
                        times = skill_hits
                        damage_by_hit = final_damage
                        total_damage = final_damage# * times

                    results.append({
                        "round": i+1,
                        "label": label,
                        "formula": full_formula,
                        "skill_result": skill_result,
                        "damage_by_hit": damage_by_hit,
                        "total_damage": total_damage,
                        "times": times,
                        "user_attack_element": user_attack_element,
                    })

                except Exception as e:
                    print(f"錯誤 [{i+1}/{repeat_count}]：", e)

            return results
       
        
        
        results = []
        results.extend(compute_and_record_damage(
            formula=formula_str,
            repeat_count=1 if skill_hits < 0 else skill_hits,
            bonus_add=bonus_add,
            bonus_step=bonus_step,
            label="main",
            skill_hits=skill_hits,  # 加入這個
            user_attack_element=User_attack_element
        ))
        
        
        # === [5] combo 計算（如果有）
        # Combo 技能
        if pd.notna(skill_row.get("combo")) and pd.notna(skill_row.get("combo_hits")):
            
            combo_formula = str(skill_row["combo"]).strip()
            raw_combo_hits = parse_hits(skill_row["combo_hits"], Sklv)


            if raw_combo_hits < 0:
                combo_hits = abs(raw_combo_hits)
                label = "combo (均分)"
            else:
                combo_hits = raw_combo_hits
                label = "combo"
            # === ✅ 套用 combo_element 若存在，暫時覆蓋 User_attack_element
            
            if pd.notna(skill_row.get("combo_element")):
                try:
                    User_attack_element = int(skill_row["combo_element"])
                    print(f"⚡ combo_element 套用屬性：{element_map.get(User_attack_element, User_attack_element)}")
                    
                except Exception as e:
                    print(f"combo_element 解析錯誤：{e}")
            

            results.extend(compute_and_record_damage(
                formula=combo_formula,
                repeat_count=combo_hits,
                bonus_add=0,
                bonus_step=0,
                label=label,
                skill_hits=raw_combo_hits,  # 注意！保留原始值讓內部處理是否均分
                user_attack_element=combo_element
            ))




        if results:
            self.skill_formula_result_input.setText(f"{results[0]['skill_result']} %")
        else:
            self.skill_formula_result_input.setText("0%")
            self.custom_calc_box.setPlainText("錯誤：無技能公式或是公式錯誤計算結果為0！")
        """
        for r in results:
            #print(f"=== 第 {r['round']} 次 ===")
            print(f"公式: {r['formula']}")
            #print(f"技能倍率: {r['skill_result']} %")
            #print(f"單次傷害: {r['damage_by_hit']}")
            #print(f"打擊次數: {r['times']} 次")
            print(f"總傷害: {r['total_damage']}")
            #print("--------------------------")
        """


         
        #=========================魔法各增傷計算顯示區=======================
        #print(f"前MATK: {MATKF} 後MATK:{MATKC} 武器MATK:{MATK_Mweapon} S.MATK:{SMATK_total}")  
        print(f"打擊次數：{len(results)}")        
        result.append(f"{pad_label('使用技能:')}{selected_skill_name}")
        if not results:
            result.append("❌ 無法計算技能傷害，請檢查公式與變數")
            return

        # 預備總傷害合計
        all_total_damage = 0

        # 判斷是否存在 combo 均分段（技能 times > 1 且每段是均分）
        combo_split_results = [r for r in results[1:] if r["times"] > 1 and r["damage_by_hit"] * r["times"] == r["total_damage"]]

        # === 情境：主技能 + combo 均分段 ===
        if len(results) > 1 and combo_split_results:
            # 顯示主技能段
            r = results[0]
            main_element_name = element_map.get(r["user_attack_element"], f"未知({r['user_attack_element']})")
            result.append(f"【{main_element_name}】==================主技能總傷害===========================")
            result.append(f"單次傷害:     {r['damage_by_hit']:,}")
            result.append(f"打擊次數:     {r['times']} 次")
            result.append(f"主技能總傷害: {r['total_damage']:,}")
            all_total_damage += r['total_damage']

            # 顯示 combo 均分段（只取第一段為代表）
            r = combo_split_results[0]
            combo_total = r["damage_by_hit"] * r["times"]
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】===============COMBO 技能（均分）========================")
            result.append(f"單次傷害(COMBO): {r['damage_by_hit']:,}")
            result.append(f"打擊次數(COMBO): {r['times']} 次")
            result.append(f"總傷害(COMBO):   {combo_total:,}")
            all_total_damage += combo_total

            # 顯示合計
            result.append(f" ")
            #result.append(f"============================總傷害合計=============================")
            result.append(f"總傷害:   {all_total_damage:,}")

        # === 正常多段技能（非均分）===
        elif len(results) > 1:
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】===========以下總傷害數值（共 {len(results)} 次）====================")
            for idx, r in enumerate(results, start=1):
                result.append(f"第 {idx}/{len(results)} 次傷害: {r['total_damage']:,}")
                all_total_damage += r['total_damage']
                # result.append(f"------------------------------------------------------------------")
            result.append(f"總傷害:   {all_total_damage:,}")

        # === 單段技能 ===
        else:
            r = results[0]
            result.append(f"【{element_map.get(User_attack_element, User_attack_element)}】=================以下總傷害數值===========================")
            result.append(f"單次傷害: {r['damage_by_hit']:,}")
            result.append(f"打擊次數: {r['times']} 次")
            result.append(f"總傷害:   {r['total_damage']:,}")





        # ✅ 加上 decay_hits 顯示處理
        decay_hits = int(skill_row["decay_hits"]) if pd.notna(skill_row.get("decay_hits")) else 0
        print(f"遞減次數：{decay_hits}")
        if decay_hits > 1:
            avg_damage = int(all_total_damage / decay_hits)
            result.append(f"遞減段數: {decay_hits} 段")
            result.append(f"平均每段傷害: {avg_damage:,}")
            #result.append(f"總傷害:   {avg_damage * decay_hits:,}")

        if attack_type == "magic":
            self.def_label.setVisible(False)
            self.def_input.setVisible(False)
            self.defc_label.setVisible(False)
            self.defc_input.setVisible(False)
            self.res_label.setVisible(False)
            self.res_input.setVisible(False)
            self.mdef_label.setVisible(True)
            self.mdef_input.setVisible(True)
            self.mdefc_label.setVisible(True)
            self.mdefc_input.setVisible(True)
            self.mres_label.setVisible(True)
            self.mres_input.setVisible(True)
            result.append(f"=========================以下各增傷數值===========================")
            result.append(f"{pad_label('前MATK:')}{MATKF:,}")
            result.append(f"{pad_label('後MATK:')}{MATKC:,}")
            result.append(f"{pad_label('武器MATK:')}{MATK_Mweapon:,}")
            result.append(f"{pad_label('裝備MATK+魔力:')}{armorMATK_MAGICPOWER}")
            result.append(f"{pad_label('MATK%:')}{round(MATK_percent)}%")
            result.append(f"{pad_label('魔法體型:')}{round(get_effect_multiplier('MD_size', target_size))}%")
            result.append(f"{pad_label('魔法屬性敵人:')}{round(get_effect_multiplier('MD_element', target_element) + get_effect_multiplier('MD_element', 10))}%")
            result.append(f"{pad_label('屬性魔法:')}{round(get_effect_multiplier('MD_Damage', User_attack_element) + get_effect_multiplier('MD_Damage', 10))}%")
            result.append(f"{pad_label('魔法種族:')}{round(get_effect_multiplier('MD_Race', target_race) + get_effect_multiplier('MD_Race', 9999))}%")
            result.append(f"{pad_label('魔法階級:')}{round(get_effect_multiplier('MD_class', target_class))}%")
            result.append(f"{pad_label('魔物增傷:')}{round(target_monsterDamage)}%")
            result.append(f"{pad_label('S.MATK:')}{round(SMATK_total)}")
            result.append(f"{pad_label('技能倍率:')}{results[0]['skill_result']}%")
            result.append(f"{pad_label('屬性倍率:')}{get_damage_multiplier(User_attack_element, target_element, target_element_lv)}%")
            result.append(f"{pad_label('前MDEF:')}{target_mdef}")
            result.append(f"{pad_label('無視魔法階級防禦:')}{round(get_effect_multiplier('MD_class_def', target_class))}%")
            result.append(f"{pad_label('無視魔法種族防禦:')}{round(get_effect_multiplier('MD_Race_def', target_race))}%")
            result.append(f"{pad_label('魔法破防後傷害:')}{Mdamage_nomdef * 100:.2f}%")
            result.append(f"{pad_label('後MDEF:')}{target_mdefc}")
            result.append(f"{pad_label('MRES:')}{target_mres}")
            result.append(f"{pad_label('無視魔法抗性%:')}{mres_reduction}%")
            result.append(f"{pad_label('魔法破抗性後傷害:')}{Mdamage_nomres * 100:.2f}%")
        
        elif attack_type == "physical":
            self.def_label.setVisible(True)
            self.def_input.setVisible(True)
            self.defc_label.setVisible(True)
            self.defc_input.setVisible(True)
            self.res_label.setVisible(True)
            self.res_input.setVisible(True)
            self.mdef_label.setVisible(False)
            self.mdef_input.setVisible(False)
            self.mdefc_label.setVisible(False)
            self.mdefc_input.setVisible(False)
            self.mres_label.setVisible(False)
            self.mres_input.setVisible(False)
            result.append(f"=========================以下各增傷數值===========================")
            if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
                result.append(f"{pad_label('前ATK (DEX系):')}{FATK:,}")
            else:#STR系
                result.append(f"{pad_label('前ATK(STR系):')}{NATK:,}")
            result.append(f"{pad_label('後ATK:')}{AKTC:,}")
            result.append(f"{pad_label('武器ATK:')}{ATK_Mweapon:,}")
            result.append(f"{pad_label('物理ATK%:')}{round(ATK_percent)}%")
            result.append(f"{pad_label('物理體型:')}{round(get_effect_multiplier('D_size', target_size))}%")
            result.append(f"{pad_label('物理種族:')}{round(get_effect_multiplier('D_Race', target_race) + get_effect_multiplier('D_Race', 9999))}%")
            result.append(f"{pad_label('物理階級:')}{round(get_effect_multiplier('D_class', target_class))}%")
            result.append(f"{pad_label('P.ATK:')}{round(patk_total)}")
            result.append(f"{pad_label('物理屬性敵人:')}{round(get_effect_multiplier('D_element', target_element) + get_effect_multiplier('D_element', 10))}%")
            result.append(f"{pad_label('爆傷:')}{round(Damage_CRI)}%")
            if weapon_class in (11,13,14,17,18,19,20,21):#DEX系
                result.append(f"{pad_label('遠傷:')}{round(RangeAttackDamage)}%")
            else:#STR系
                result.append(f"{pad_label('近傷:')}{round(MeleeAttackDamage)}%")
            result.append(f"{pad_label('CRATE:')}{round(total_CRATE)}")
            result.append(f"{pad_label('技能倍率:')}{results[0]['skill_result']}%")
            result.append(f"{pad_label('屬性倍率:')}{get_damage_multiplier(User_attack_element, target_element, target_element_lv)}%")
            result.append(f"{pad_label('武器體型修正:')}{Weaponpunish*100}%")
            #result.append(f"{pad_label('前DEF:')}{target_def}")
            result.append(f"{pad_label('無視階級防禦:')}{round(get_effect_multiplier('D_class_def', target_class))}%")
            result.append(f"{pad_label('無視種族防禦:')}{round(get_effect_multiplier('D_Race_def', target_race))}%")
            #result.append(f"{pad_label('魔法破防後傷害:')}{Mdamage_nomdef * 100:.2f}%")
            #result.append(f"{pad_label('後DEF:')}{target_mdefc}")
            #result.append(f"{pad_label('RES:')}{target_mres}")
            #result.append(f"{pad_label('無視物理抗性%:')}{mres_reduction}%")
            #result.append(f"{pad_label('物理破抗性後傷害:')}{Mdamage_nomres * 100:.2f}%")
            

            
        else:
            raise ValueError(f"未知的攻擊類型: {attack_type}")
            
                        
        result.append(f"{pad_label('技能增傷(裝備段):')}{round(Use_Skills)}%")
        result.append(f"{pad_label('技能增傷(技能段):')}{round(passive_skill_buff)}%")
        result.append(f"==================================================================")
        result.append(f"{pad_label('技能等級:')}{Sklv}")
        #result.append(f"{pad_label('技能公式:')}{results[0]['formula']}")
        


        result.extend(bottom_result)#顯示前面儲存的公式
        self.custom_calc_box.setHtml(self.generate_highlighted_html(result))
        if self.auto_compare_checkbox.isChecked():
            self.compare_with_base()
        #self.custom_calc_box.setPlainText("\n".join(result))





    def generate_highlighted_html(self, lines: list[str]) -> str:
        app = QApplication.instance()        
        if not app:
            raise RuntimeError("QApplication 尚未建立")

        palette = app.palette()
        window_color: QColor = palette.color(QPalette.Window)
        text_color: QColor = palette.color(QPalette.WindowText)

        # 根據亮度判斷主題
        # 若背景偏暗（亮度 < 128），則視為暗色模式
        brightness = (window_color.red() * 0.299 + window_color.green() * 0.587 + window_color.blue() * 0.114)
        dark_mode = brightness < 128

        if dark_mode:
            odd_color = "#FFFFFF"   # 白字
            even_color = "#AAAAAA"  # 灰字
        else:
            odd_color = "#000000"   # 黑字
            even_color = "#555555"  # 深灰字

        html_lines = []
        for i, line in enumerate(lines):
            color = even_color if i % 2 else odd_color
            html_lines.append(f'<span style="color:{color};">{line}</span>')

        html_result = (
            "<pre style='font-family: MingLiU; font-size: 11pt;'>\n"
            + "\n".join(html_lines)
            + "\n</pre>"
        )

        return html_result


        
    def apply_effect_mapping(self, effect_dict, prefix, names, key_template, index_override=None):
        for i, name in enumerate(names):
            idx = index_override[i] if index_override else i
            key = (key_template.format(name), "%")
            value = sum(val for val, _ in effect_dict.get(key, []))
            setattr(self, f"{prefix}_{idx}", value)

    def apply_all_damage_effects(self, effect_dict):
        # === 體型加成 ===
        size_names = ["小型", "中型", "大型"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_size", size_names, f"對 {{}} 敵人的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 屬性對象加成 ===
        element_target = ["無屬性", "水屬性", "地屬性", "火屬性", "風屬性",
                          "毒屬性", "聖屬性", "暗屬性", "念屬性", "不死屬性", "全屬性"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_element", element_target, f"對 {{}} 對象的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 屬性來源加成（屬性攻擊） ===
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Damage", element_target, f"{{}} 的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 種族加成 ===
        race_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race", race_names, f"對 {{}} 型怪的{ '魔法' if prefix == 'MD' else '物理' }傷害", race_indexes)

        # === 階級加成 ===
        class_names = ["一般", "首領"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_class", class_names, f"對 {{}} 階級的{ '魔法' if prefix == 'MD' else '物理' }傷害")

        # === 無視階級防禦 ===
        class_def_names = ["一般", "首領", "玩家"]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_class_def", class_def_names, f"無視 {{}} 階級的{ '魔法' if prefix == 'MD' else '物理' }防禦")

        # === 無視種族防禦 ===
        race_def_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race_def", race_def_names, f"無視 {{}} 的{ '魔法' if prefix == 'MD' else '物理' }防禦", race_indexes)
        
        # === 無視種族抗性 ===
        race_def_names = ["無形", "不死", "動物", "植物", "昆蟲", "魚貝", "惡魔", "人形", "天使", "龍族", "全種族"]
        race_indexes = list(range(10)) + [9999]
        for prefix in ["MD", "D"]:
            self.apply_effect_mapping(effect_dict, f"{prefix}_Race_res", race_def_names, f"無視 {{}} 的{ '魔法' if prefix == 'MD' else '物理' }抗性", race_indexes)

    
    def calc_weapon_refine_matk(self, weapon_Level, weaponRefineR, weaponGradeR):
        """
        回傳： (MATK 總加成, S.MATK 總加成)
        說明：
          1~4 階：每 +1 固定加成；超過安定值後，每 +1 額外給「浮動加成(取上限)」；
                  若精煉 > 15，則每超過 1 級，對「1~15」再各加一次 over16_bonus，共 15 倍。
          5 階：依品級每 +1 固定 MATK，加上每 +1 固定 +2 S.MATK。
        """
        if weapon_Level == 0 or weaponRefineR <= 0:
            return 0, 0

        # 每精煉+1 增加 MATK
        base_per_refine   = {1: 2, 2: 3, 3: 5, 4: 7, 5: 0}
        # 超過安定值後，每 +1 額外「浮動」增加的上限值
        extra_after_safe  = {1: 3, 2: 5, 3: 8, 4: 14, 5: 0}
        # 精煉 16 以上，每超過 1 級，對 1~15 各再加的數值
        over16_bonus      = {1: 3, 2: 5, 3: 7, 4: 10, 5: 0}
        # 安定值
        safe_threshold    = {1: 7, 2: 6, 3: 5, 4: 4, 5: 0}

        # 五階各品級的每 +1 MATK
        level5_grade_bonus = {
            0: 8.0,   # N
            1: 8.8,   # D
            2: 10.4,  # C
            3: 12.0,  # B
            4: 16.0   # A
        }
        # 五階每 +1 固定 +2 S.MATK
        smatk_bonus_per_refine = 2

        matk_total = 0.0
        smatk_total = 0.0

        if weapon_Level < 5:
            # 固定加成：所有等級都算
            base = weaponRefineR * base_per_refine[weapon_Level]

            # 浮動加成：只在超過安定值的那幾級才算（取上限）
            safe = safe_threshold[weapon_Level]
            steps_after_safe = max(0, weaponRefineR - safe)
            variance = steps_after_safe * extra_after_safe[weapon_Level]

            # 16 以上額外加成：每超過 1 級，對「1~15」各再加一次（= 15 倍）
            steps_over16 = max(0, weaponRefineR - 15)
            over16 = steps_over16 * 15 * over16_bonus[weapon_Level]

            #matk_total = base + variance + over16
            matk_total = base + over16#安定後浮動加成暫時取消
            smatk_total = 0.0

        else:  # weapon_Level == 5
            matk_per_refine = level5_grade_bonus.get(weaponGradeR, 0.0)
            matk_total = weaponRefineR * matk_per_refine
            smatk_total = weaponRefineR * smatk_bonus_per_refine

        return matk_total, smatk_total
        
    def calc_weapon_refine_atk(self, weapon_Level, weaponRefineR, weaponGradeR):
        """
        回傳： (ATK/MATK 總加成, P.ATK/S.MATK 總加成)
        說明：
          1~4 階：每 +1 固定加成；超過安定值後，每 +1 額外給「浮動加成(這裡取上限)」；
                  若精煉 > 15，則每超過 1 級，對「1~15」再各加一次 over16_bonus，共 15 倍。
          5 階：依品級每 +1 固定 ATK/MATK，加上每 +1 固定 +2 P.ATK/S.MATK。
        """
        if weapon_Level == 0 or weaponRefineR <= 0:
            return 0, 0

        # 每精煉+1 增加 ATK/MATK
        base_per_refine   = {1: 2, 2: 3, 3: 5, 4: 7, 5: 0}
        # 超過安定值後，每 +1 額外「浮動」增加的上限值（表格中的 1~X，這裡取 X 當上限）
        extra_after_safe  = {1: 3, 2: 5, 3: 8, 4: 14, 5: 0}
        # 精煉 16 以上，每超過 1 級，對 1~15 各再加的數值
        over16_bonus      = {1: 3, 2: 5, 3: 7, 4: 10, 5: 0}
        # 安定值
        safe_threshold    = {1: 7, 2: 6, 3: 5, 4: 4, 5: 4}

        # 五階各品級的每 +1 ATK/MATK
        level5_grade_bonus = {
            0: 8.0,   # N
            1: 8.8,   # D
            2: 10.4,  # C
            3: 12.0,  # B
            4: 16.0   # A
        }
        # 五階每 +1 固定 +2 P.ATK/S.MATK
        patk_bonus_per_refine = 2

        atk_total = 0.0
        patk_total = 0.0

        if weapon_Level < 5:
            # 固定加成：所有等級都算
            base = weaponRefineR * base_per_refine[weapon_Level]

            # 浮動加成：只在超過安定值的那幾級才算（這裡取“上限”值）
            safe = safe_threshold[weapon_Level]
            steps_after_safe = max(0, weaponRefineR - safe)
            variance = steps_after_safe * extra_after_safe[weapon_Level]

            # 16 以上額外加成：每超過 1 級，對「1~15」各再加一次（= 15 倍）
            steps_over16 = max(0, weaponRefineR - 15)
            over16 = steps_over16 * 15 * over16_bonus[weapon_Level]

            #atk_total = base + variance + over16
            atk_total = base + over16#安定後浮動加成暫時取消
            patk_total = 0.0

        else:  # weapon_Level == 5
            atk_per_refine = level5_grade_bonus.get(weaponGradeR, 0.0)
            atk_total = weaponRefineR * atk_per_refine
            patk_total = weaponRefineR * patk_bonus_per_refine

        return atk_total, patk_total



    def update_note_widget_with_delay(self, widget: QTextEdit, text: str):
        widget.setPlainText(text)

        def adjust():
            # ✅ 強制文字寬度套入 layout
            widget.document().setTextWidth(widget.viewport().width())
            self.adjust_textedit_height(widget)

        # 雙層 QTimer 保證 Qt 已繪製完畢
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, adjust))

    def adjust_textedit_height(self, text_edit: QTextEdit):
        doc = text_edit.document()

        # 🔧 強制 layout
        doc.setTextWidth(text_edit.viewport().width())
        doc.adjustSize()  # 👈 這個是 Qt layout 關鍵

        text_edit.updateGeometry()
        text_edit.update()

        # 重新取得 layout 後的尺寸
        line_count = doc.blockCount()
        doc_size = doc.size().toSize()

        #print(f"📝 [{text_edit.objectName()}] 目前行數：{line_count}")
        #print(f"📐 Document size: {doc_size.width()} x {doc_size.height()}")

        margin = 3
        min_height = 27
        max_height = 400
        new_height = max(min_height, min(doc_size.height() + margin, max_height))

        #print(f"🪄 設定高度為：{new_height}")
        text_edit.setFixedHeight(new_height)



    def on_function_text_changed(self):
        
        sender = self.sender()  # 取得是哪個 QTextEdit 被改了
        if not sender:
            return

        object_name = sender.objectName()  # 例如 "頭上-函數"
        if not object_name.endswith("-函數"):
            return

        part_name = object_name.replace("-函數", "")
        lua_code = sender.toPlainText()

        #print(f"🔍 偵測到 {object_name} 變動，內容：\n{lua_code}")

        try:
            results = parse_lua_effects_with_variables(
                block_text=lua_code,
                refine_inputs={},
                get_values={},
                grade=0,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                hide_unrecognized=False
            )
            output = "\n".join(results)
        except Exception as e:
            output = f"⚠️ 錯誤：{e}"

        # 尋找對應的 詞條 欄位，名稱是 part_name-詞條
        target_name = f"{part_name}-詞條"
        for v in self.refine_inputs_ui.values():
            if v.get("note_ui") and v["note_ui"].objectName() == target_name:
                v["note_ui"].setPlainText(output)
                QTimer.singleShot(0, lambda w=v["note_ui"]: self.adjust_textedit_height(w))
                break
        

    def handle_note_text_clicked(self, event, part_name, text_widget_ui ,text_widget):
        self.clear_current_edit()
        self.current_edit_part = f"{part_name} - 詞條"
        self.current_edit_widget = text_widget
        self.current_edit_label.setText(f"目前部位：{self.current_edit_part}")
        print(f"目前部位：{self.current_edit_part}")
        self.unsync_button.setVisible(True)
        self.apply_to_note_button.setVisible(True)
        self.clear_field_button2.setVisible(True)
        self.unsync_button2.setVisible(True)
        self.apply_equip_button.setVisible(True)
        self.clear_field_button.setVisible(True)

        self.set_edit_lock(part_name, "note")
        for v in self.refine_inputs_ui.values():
            if "note" in v:
                v["note"].setStyleSheet("")
        text_widget_ui.setStyleSheet("background-color: #ff0000;")

        self.result_output.setPlainText(text_widget.toPlainText())
        self.tab_widget.setCurrentIndex(self.function_tab_index)

        QTextEdit.mousePressEvent(text_widget, event)  # 保留原始點擊事件行為


    def update_function_selector(self):
        self.function_selector.clear()
        for func_name, spec in function_defs.items():
            label = spec.get("desc", func_name)  # 顯示用中文描述
            self.function_selector.addItem(label, func_name)

        if self.function_selector.count() > 0:
            self.function_selector.setCurrentIndex(0)
            self.on_function_changed()

            
    def on_tab_changed(self, index):
        if index == self.function_tab_index:
            self.update_function_selector()
            self.update_all_notes_from_functions()  # ⬅️ 加這一行

        self.tab_widget.adjustSize()

        QTimer.singleShot(50, lambda: (
            self.tab_widget.repaint(),
        ))

    def update_all_notes_from_functions(self):
        for part_name, widgets in self.refine_inputs_ui.items():
            function_widget = widgets.get("function")
            note_widget = widgets.get("note_ui")
            if not function_widget or not note_widget:
                continue

            lua_code = function_widget.toPlainText()

            try:
                results = parse_lua_effects_with_variables(
                    block_text=lua_code,
                    refine_inputs={},
                    get_values={},
                    grade=0,
                    unit_map=unit_map,
                    size_map=size_map,
                    effect_map=effect_map,
                    hide_unrecognized=False
                )
                output = "\n".join(results)
            except Exception as e:
                output = f"⚠️ 錯誤：{e}"

            self.update_note_widget_with_delay(note_widget, output)


    def clear_global_state(self):#清除全域武器裝備技能等級並預先匯入基礎值
        #print("武器階級：", global_weapon_level_map)
        #print("防具階級：", global_armor_level_map)
        #print("武器類型：", global_weapon_type_map)
        #print("技能：", enabled_skill_levels)
        global_weapon_level_map.clear()
        global_armor_level_map.clear()
        global_weapon_type_map.clear()
        
        
        enabled_skill_levels.clear()
       # 你目前已知使用的 slot ID 範圍
        slot_ids = [10, 11, 12, 2, 4, 3, 5, 6, 7, 8,
                    30, 31, 32, 33, 34, 35, 41, 42, 43, 44]

        for slot in slot_ids:
            global_weapon_level_map[slot] = 0
            global_armor_level_map[slot] = 0
            global_weapon_type_map[slot] = 0
        #self.update_combobox()

        #self.display_item_info()
        #self.display_all_effects()
        #self.update_all_notes_from_functions
        #self.replace_custom_calc_content
        #self.on_function_text_changed
        #print("清除完畢：============================")
        #print("武器階級：", global_weapon_level_map)
        #print("防具階級：", global_armor_level_map)
        #print("武器類型：", global_weapon_type_map)
        #print("技能：", enabled_skill_levels)

    def update_dex_int_half_note(self):
        raw_effects = getattr(self, "effect_dict_raw", {})

        # 取得 base 值
        try:
            base_dex = int(self.input_fields["DEX"].text())
        except:
            base_dex = 0
        try:
            base_int = int(self.input_fields["INT"].text())
        except:
            base_int = 0

        # 取得 JOB 加成
        job_id = self.input_fields["JOB"].currentData()
        tjob_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
        dex_job = tjob_bonus[4] if len(tjob_bonus) > 4 else 0  # DEX index = 4
        int_job = tjob_bonus[3] if len(tjob_bonus) > 3 else 0  # INT index = 3

        # 裝備加成從 effect_dict_raw 拿
        dex_equip = sum(val for val, _ in raw_effects.get(("DEX", ""), []))
        int_equip = sum(val for val, _ in raw_effects.get(("INT", ""), []))

        dex_total = base_dex + dex_job + dex_equip
        int_total = base_int + int_job + int_equip

        result = dex_total + int(int_total / 2)
        status = "✅" if result >= 265 else "⚠️ 未達標"

        self.DEX_INT_265_label.setText(
            f"※素質無詠 {dex_total} + {int(int_total/2)} = {result} {status}"
        )
    def safe_update_textbox(self, textbox, text):
        scrollbar = textbox.verticalScrollBar()
        scroll_pos = scrollbar.value()
        textbox.setPlainText(text)
        scrollbar.setValue(scroll_pos)

    def toggle_equip_text_visibility(self):
        hidden = self.hide_unrecognized_checkbox.isChecked()
        self.equip_text.setVisible(not hidden)
        self.equip_text_label.setVisible(not hidden)
        
    def filter_effects(self, effects: list[str]) -> list[str]:
        hide_keywords = []
        if self.hide_physical_checkbox.isChecked():
            hide_keywords.extend(["物理", "爆擊", "CRI", "武器ATK" , "P.ATK"])
        if self.hide_magical_checkbox.isChecked():
            hide_keywords.extend(["魔法", "武器MATK", "S.MATK"])

        # 過濾物理/魔法關鍵字
        filtered = [line for line in effects if not any(k in line for k in hide_keywords)]

        # 過濾未辨識或需隱藏內容
        if self.hide_unrecognized_checkbox.isChecked():
            filtered = [
                line for line in filtered
                if not (line.startswith("🟡") or
                        line.startswith("⚠️") or
                        line.startswith("❌") or
                        line.startswith("📌") or
                        line.startswith("✅") or
                        line.startswith("⛔"))
            ]
        return filtered
    
    def filter_skill_list(self):
        keyword = self.skill_search_bar.text().strip().lower()

        for name, checkbox in self.skill_checkboxes.items():
            if keyword in name.lower() or keyword in all_skill_entries[name]["type"].lower():
                checkbox.show()
            else:
                checkbox.hide()


    
    def normalize_effect_key(self, key: str) -> str:
        key = key.strip()

        # 只處理 固定 / 變動 詠唱
        key = key.replace("固定詠唱時間", "固定詠唱時間")
        key = key.replace("變動詠唱時間", "變動詠唱時間")

        return key


    def try_extract_effect(self, line: str):
        import re

        # 統一處理 % 類型（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9]+)\%$", line)
        if match:
            return match.group(1).strip(), int(match.group(2)), "%"

        # 處理 秒 類型（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9.]+)\s*秒$", line)
        if match:
            return match.group(1).strip(), float(match.group(2)), "秒"

        # 處理 無單位數值（+/-）
        match = re.match(r"(.+?)\s*([+-]?[0-9]+)$", line)
        if match:
            return match.group(1).strip(), int(match.group(2)), ""

        return None
        
    def update_stat_bonus_display(self):
        try:
            job_id = self.input_fields["JOB"].currentData()
            tjob_bonus = job_dict.get(job_id, {}).get("TJobMaxPoint", [])
            stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT"]

            raw_effects = getattr(self, "effect_dict_raw", {})

            for i, stat in enumerate(stat_names):
                job = tjob_bonus[i] if i < len(tjob_bonus) else 0
                try:
                    base = int(self.input_fields[stat].text())
                except:
                    base = 0

                entries = raw_effects.get((stat, ""), [])
                equip = sum(val for val, _ in entries)
                total = base + job + equip

                if stat in self.stat_bonus_labels:
                    self.stat_bonus_labels[stat].setFont(QFont("Consolas", 14))
                    self.stat_bonus_labels[stat].setText(f"{base:>3} +{job:>3} +{equip:>3} = {total:>3}")
        except Exception as e:
            print("顯示職業加成錯誤：", e)


    def calculate_tstat_total_used(self):
        total = 0
        for tstat in ["POW", "STA", "WIS", "SPL", "CON", "CRT"]:
            try:
                val = int(self.input_fields[tstat].text())
            except:
                val = 0
            total += val  # ✅ 每一點直接 +1
        return total

    def on_result_output_changed(self):
        if isinstance(self.result_output, QTextEdit):
            lua_code = self.result_output.toPlainText()
        else:
            lua_code = self.result_output.text()

        # === get(x) 對應 ===
        get_values = {}
        for stat_name, stat_id in self.stat_fields.items():
            try:
                get_values[stat_id] = int(self.input_fields[stat_name].text())
            except:
                get_values[stat_id] = 0

        # === refine_inputs: 所有部位 slot ➜ 精煉值 ===
        refine_inputs = {}
        for part_name, info in self.refine_parts.items():
            slot_id = info.get("slot")
            try:
                refine_inputs[slot_id] = self.refine_inputs_ui[part_name]["refine"].value()
            except:
                refine_inputs[slot_id] = 0

        # === 全域精煉 slot（GetLocation() 用）===
        try:
            current_location_slot = self.global_refine_input()
        except:
            current_location_slot = 0

        # === 全域階級（GetEquipGradeLevel(GetLocation()) 用）===
        try:
            grade = self.global_grade_combo.currentData()
        except:
            grade = 4

        try:
            results = parse_lua_effects_with_variables(
                block_text=lua_code,
                refine_inputs=refine_inputs,
                get_values=get_values,
                grade=grade,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                current_location_slot=current_location_slot  # ✅ 傳入現在位置 slot
            )
            results = self.filter_effects(results)
            explanation = "\n".join(results)
        except Exception as e:
            explanation = f"⚠️ 錯誤：{e}"

        self.syntax_result_box.setPlainText(explanation)




    def on_function_changed(self):
        self.skill_search_input.setVisible(False)
        func_name = self.function_selector.currentData()
        spec = function_defs.get(func_name, {})
        self.param_widgets.clear()

        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_layout = QHBoxLayout()

        for arg in spec.get("args", []):
            if arg.get("name") in ("無意義", "目標"):
                if arg.get("map") == "unit_map":
                    # 特殊情況：map 是 unit_map → 強制指定 1
                    self.param_widgets.append("1")
                elif "map" in arg and arg["map"].isdigit():
                    # 一般情況：map 本身就是數字字串
                    self.param_widgets.append(arg["map"])
                else:
                    # 其他情況：預設填 0
                    self.param_widgets.append("0")
                continue



            label = QLabel(arg["name"])
            row_layout.addWidget(label)

            if "map" in arg:
                if arg["map"].isdigit():
                    label_value = QLabel(f"(固定: {arg['map']})")
                    label_value.setObjectName("fixed")
                    self.param_widgets.append(arg["map"])
                    row_layout.addWidget(label_value)
                    row_layout.setFixedWidth(150)
                    
                elif arg["map"]:
                    if arg["map"] == "skill_map":
                        # ✅ 技能選單 + 外部搜尋框綁定
                        self.skill_search_input.setVisible(True)
                        combo = QComboBox()
                        combo.setFixedWidth(150)
                        combo.setEditable(False)

                        try:
                            value_map = eval(arg["map"])
                        except Exception:
                            value_map = {}
                            

                        all_items = list(value_map.items())
                        for k, v in all_items:
                            combo.addItem(v, k)

                        def filter_skill_combo():
                            keyword = self.skill_search_input.text().lower().strip()
                            combo.clear()
                            for k, v in all_items:
                                if keyword in v.lower() or keyword in str(k):
                                    combo.addItem(v, k)
                        try:
                            self.skill_search_input.textChanged.disconnect()
                        except TypeError:
                            pass
                        self.skill_search_input.textChanged.connect(filter_skill_combo)

                        self.param_widgets.append(combo)
                        row_layout.addWidget(combo)

                    else:
                        combo = QComboBox()
                        combo.setFixedWidth(150)
                        try:
                            value_map = eval(arg["map"])

                            if arg["map"] == "effect_map":
                                # 只有 effect_map 時才按名稱排序
                                items = sorted(value_map.items(), key=lambda item: item[1])
                            else:
                                items = value_map.items()

                            for k, v in items:
                                combo.addItem(v, k)

                        except Exception:
                            combo.addItem("（錯誤：找不到 map）", -1)
                        
                        self.param_widgets.append(combo)
                        row_layout.addWidget(combo)
                
            elif arg.get("type") == "value":
                spin = QSpinBox()
                spin.setRange(0, 999)
                spin.setFixedWidth(45)
                spin.setButtonSymbols(QSpinBox.NoButtons)
                spin.wheelEvent = lambda e: None
                self.param_widgets.append(spin)
                row_layout.addWidget(spin)

        row_widget = QWidget()
        row_widget.setLayout(row_layout)
        self.param_layout.addWidget(row_widget, alignment=Qt.AlignRight)




    

    def on_generate(self):
        func_name = self.function_selector.currentData()
        args = []
        for w in self.param_widgets:
            if isinstance(w, QComboBox):
                args.append(str(w.currentData()))
            elif isinstance(w, QSpinBox):
                args.append(str(w.value()))
            elif isinstance(w, str):  # 固定值
                args.append(w)
        result = f"{func_name}({', '.join(args)})"

        # ✅ 新增一行，不覆蓋
        existing = self.result_output.toPlainText()
        if existing.strip():
            new_text = existing + "\n" + result
        else:
            new_text = result
        self.result_output.setPlainText(new_text)

        # ✅ 自動捲到底（可選）
        self.result_output.verticalScrollBar().setValue(
            self.result_output.verticalScrollBar().maximum()
        )





    def recompile(self):
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle("確認重新編譯")
        msgbox.setText(
            "這將刪除以下兩個檔案並重新編譯：\n\n"
            "・EquipmentProperties.lua\n"
            "・iteminfo_new.lua\n\n是否繼續？"
        )
        yes_button = msgbox.addButton("是", QMessageBox.YesRole)
        cancel_button = msgbox.addButton("取消", QMessageBox.RejectRole)
        msgbox.exec()

        if msgbox.clickedButton() == yes_button:
            try:
                data_folder = os.path.join(os.getcwd(), "DATA")
                files_to_delete = ["EquipmentProperties.lua", "iteminfo_new.lua"]

                for filename in files_to_delete:
                    filepath = os.path.join(data_folder, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)

                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("重新編譯")
                msgbox.setText("檔案已刪除，程式將重新啟動以重新編譯。")
                ok_button = msgbox.addButton("確定", QMessageBox.AcceptRole)
                msgbox.exec()

                python = sys.executable
                os.execl(python, python, *sys.argv)

            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"發生錯誤：{str(e)}")

    def update_total_effect_display(self):
        keyword = self.total_filter_input.text().strip()
        if not keyword:
            lines = self.total_combined_raw
        else:
            lines = [line for line in self.total_combined_raw if keyword in line]

        self.safe_update_textbox(self.total_effect_text, "\n".join(lines))
        
    #被動技能給予的狀態
    def apply_skill_buffs_into_effect_dict(self, skillbuff_path, enabled_skill_levels, refine_inputs, get_values, grade):
        try:
            with open(skillbuff_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 無法讀取 skillbuff.lua：{e}")
            return {}

        effect_dict = {}
        for skill_id, level in enabled_skill_levels.items():
            pattern = rf"\[{skill_id}\]\s*=\s*\{{(.*?)\}}"
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue

            block = match.group(1)
            block = re.sub(rf"GSklv\({skill_id}\)", str(level), block)

            parsed_lines = parse_lua_effects_with_variables(
                block,
                refine_inputs,
                get_values,
                grade,
                unit_map,
                size_map,
                effect_map,
                hide_unrecognized=True
            )

            skill_name = skill_map.get(skill_id, f"技能ID {skill_id}")
            source_str = f"技能：{skill_name} Lv.{level}"

            for line in parsed_lines:
                # 嘗試匹配格式："S.MATK +5"、"固定詠唱時間 -1.0 秒"
                match = re.match(r"(.+?) ([+-]\d+(?:\.\d+)?)([%秒]?)$", line)
                if not match:
                    continue

                key, val_str, unit = match.groups()
                try:
                    value = float(val_str)
                except:
                    continue

                display_value = int(value) if value.is_integer() else round(value, 1)

                effect_dict.setdefault((key.strip(), unit), []).append((display_value, source_str))

        return effect_dict





    def display_all_effects(self):
        def extract_combi_ids(block_text: str) -> list[int]:
            import re
            match = re.search(r"Combiitem\s*=\s*{([^}]*)}", block_text)
            if match:
                return [int(i.strip()) for i in match.group(1).split(",")]
            return []

        def extract_combo_items(combo_text: str) -> set[int]:
            import re
            match = re.search(r"Item\s*=\s*{([^}]*)}", combo_text)
            if match:
                items = match.group(1).split(",")
                result = set()
                for x in items:
                    x = x.strip()
                    if x.isdigit():
                        result.add(int(x))
                    elif x != '':
                        print(f"⚠️ 無法轉換為整數: '{x}' in block: {combo_text}")
                return result
            return set()



        get_values = {}
        for label, gid in self.stat_fields.items():
            widget = self.input_fields[label]
            if isinstance(widget, QComboBox):
                get_values[gid] = widget.currentData()
            else:
                try:
                    get_values[gid] = int(widget.text())
                except ValueError:
                    get_values[gid] = 0

        # 🔁 等所有 stat 欄位都建立後，再註冊 textChanged
        if hasattr(self, "_update_stat_point_callback"):
            for attr in ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT", "BaseLv"]:
                self.input_fields[attr].textChanged.connect(self._update_stat_point_callback)

            # 主動執行一次，初始化顯示
            self._update_stat_point_callback()


        refine_inputs = {}
        for label, info in self.refine_parts.items():
            slot_id = info["slot"]
            try:
                refine_inputs[slot_id] = int(self.input_fields[label].text())
            except:
                refine_inputs[slot_id] = 0

        effect_dict = {}

        for part_name, ui in self.refine_inputs_ui.items():
            # ▶️ 裝備主體處理
            equip_name = ui["equip"].text().strip()
            if equip_name:
                source_label = f"{part_name}：{equip_name}"  # or 卡片名稱 or 套裝來源
                for item_id, item in self.parsed_items.items():
                    if item["name"] == equip_name and item_id in self.equipment_data:
                        block_text = self.equipment_data[item_id]
                        grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                        slot_id = self.refine_parts[part_name]["slot"]

                        effects = parse_lua_effects_with_variables(
                            block_text,
                            refine_inputs,
                            get_values,
                            grade,
                            unit_map,
                            size_map,
                            effect_map,
                            hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                            hide_physical=self.hide_physical_checkbox.isChecked(),
                            hide_magical=self.hide_magical_checkbox.isChecked(),
                            current_location_slot=slot_id
                        )

                        filtered = self.filter_effects(effects)
                        for line in filtered:
                            if not line.strip():
                                continue
                            parsed = self.try_extract_effect(line)
                            if parsed:
                                key, value, unit = parsed
                                key = self.normalize_effect_key(key)
                                

                                # 建立效果來源清單
                                effect_dict.setdefault((key, unit), []).append((value, source_label))


            # ▶️ 卡片欄處理（最多4張）
            for i, card_input in enumerate(ui["cards"]):
                grade = 0
                card_name = card_input.text().strip()
                if not card_name:
                    continue
                source_label = f"{part_name}：{card_name}"  # or 卡片名稱 or 套裝來源
                for item_id, item in self.parsed_items.items():
                    if item["name"] == card_name and item_id in self.equipment_data:
                        block_text = self.equipment_data[item_id]
                        grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                        slot_id = self.refine_parts[part_name]["slot"]
                        effects = parse_lua_effects_with_variables(
                            block_text,
                            refine_inputs,
                            get_values,
                            grade,
                            unit_map=unit_map,
                            size_map=size_map,
                            effect_map=effect_map,
                            hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                            hide_physical=self.hide_physical_checkbox.isChecked(),
                            hide_magical=self.hide_magical_checkbox.isChecked(),
                            current_location_slot=slot_id    
                        )

                        filtered = self.filter_effects(effects)
                        for line in filtered:
                            if not line.strip():
                                continue
                            parsed = self.try_extract_effect(line)
                            if parsed:
                                key, value, unit = parsed
                                key = self.normalize_effect_key(key)
                                

                                # 建立效果來源清單
                                effect_dict.setdefault((key, unit), []).append((value, source_label))
                                
            # ▶️ 詞條處理（如果有手動輸入）
            if "note" in ui:
                note_text = ui["note"].toPlainText().strip()
                if note_text:
                    grade = self.input_fields[f"{part_name}_階級"].currentIndex()
                    slot_id = self.refine_parts[part_name]["slot"]
                    source_label = f"{part_name}：詞條"

                    effects = parse_lua_effects_with_variables(
                        note_text,
                        refine_inputs,
                        get_values,
                        grade,
                        unit_map=unit_map,
                        size_map=size_map,
                        effect_map=effect_map,
                        hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                        hide_physical=self.hide_physical_checkbox.isChecked(),
                        hide_magical=self.hide_magical_checkbox.isChecked(),
                        current_location_slot=slot_id
                    )

                    filtered = self.filter_effects(effects)
                    for line in filtered:
                        if not line.strip():
                            continue
                        parsed = self.try_extract_effect(line)
                        if parsed:
                            key, value, unit = parsed
                            key = self.normalize_effect_key(key)

                            # 建立效果來源清單
                            effect_dict.setdefault((key, unit), []).append((value, source_label))


        # ▶️ 加入技能增益（例如料理等）
        for skill_name, entry in all_skill_entries.items():
            checkbox = self.skill_checkboxes.get(skill_name)
            if not checkbox or not checkbox.isChecked():
                continue  # 沒有勾選就跳過

            code_block = "\n".join(entry["code"])
            effects = parse_lua_effects_with_variables(
                code_block,
                refine_inputs,
                get_values,
                grade=0,
                unit_map=unit_map,
                size_map=size_map,
                effect_map=effect_map,
                hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                hide_physical=self.hide_physical_checkbox.isChecked(),
                hide_magical=self.hide_magical_checkbox.isChecked(),
                current_location_slot=None
            )

            source_label = f"{entry.get('type', '技能')}：{skill_name}"

            for line in self.filter_effects(effects):
                if not line.strip():
                    continue
                parsed = self.try_extract_effect(line)
                if parsed:
                    key, value, unit = parsed
                    key = self.normalize_effect_key(key)
                    effect_dict.setdefault((key, unit), []).append((value, source_label))
                    



        triggered_combos = set()
        combo_effects_all = []  # 用來儲存套裝效果（供分頁顯示）
        equipped_ids = set()  # 蒐集所有裝備物品ID（含卡片）

        # 先收集所有裝備 ID
        for part_name, ui in self.refine_inputs_ui.items():
            equip_name = ui["equip"].text().strip()
            if equip_name:
                for item_id, item in self.parsed_items.items():
                    if item["name"] == equip_name:
                        equipped_ids.add(item_id)
            for card_input in ui["cards"]:
                card_name = card_input.text().strip()
                if card_name:
                    for item_id, item in self.parsed_items.items():
                        if item["name"] == card_name:
                            equipped_ids.add(item_id)


        # 掃描每個裝備，看是否有 Combiitem 欄位
        for item_id in equipped_ids:
            block_text = self.equipment_data.get(item_id)
            if not block_text:
                continue
            combi_ids = extract_combi_ids(block_text)
            for combi_id in combi_ids:
                if combi_id in triggered_combos:
                    continue
                combo_block = self.equipment_data.get(combi_id)
                if not combo_block:
                    continue
                combo_items = extract_combo_items(combo_block)
                if combo_items.issubset(equipped_ids):
                    # ✅ 套裝條件成立，觸發效果
                    triggered_combos.add(combi_id)

                    # ✅ 生成完整的 grade dict（每個部位的 slot 與階級）
                    grade = {
                        self.refine_parts[part]["slot"]: self.input_fields[f"{part}_階級"].currentIndex()
                        for part in self.refine_parts
                    }

                    # 取得當前觸發套裝的部位 slot
                    slot_id = self.refine_parts[part_name]["slot"]

                    # 呼叫效果解析，傳入完整的 grade dict
                    effects = parse_lua_effects_with_variables(
                        combo_block,
                        refine_inputs,
                        get_values,
                        grade,  # ✅ 改為 dict
                        unit_map=unit_map,
                        size_map=size_map,
                        effect_map=effect_map,
                        hide_unrecognized=self.hide_unrecognized_checkbox.isChecked(),
                        hide_physical=self.hide_physical_checkbox.isChecked(),
                        hide_magical=self.hide_magical_checkbox.isChecked(),
                        current_location_slot=slot_id  
                    )

                    filtered = self.filter_effects(effects)
                    show_source = self.show_combo_source_checkbox.isChecked()
                    combo_items = extract_combo_items(combo_block)


                    # 將 itemid 映射成名稱
                    combo_item_names = []
                    for iid in combo_items:
                        name = self.parsed_items.get(iid, {}).get("name", f"ID:{iid}")
                        combo_item_names.append(f"[{name}]")

                    source_label = "、".join(combo_item_names) if combo_item_names else f"套裝ID {combi_id}"

                    if show_source:
                        combo_effects_all.append(f"🧩 套裝來源：{source_label}")
                        for line in filtered:
                            combo_effects_all.append(f"  {line}")
                            
                    else:
                        combo_effects_all.extend(filtered)# 加入縮排以便辨識
                        
                    for line in filtered:
                        m = re.match(r"(.+?) ([+\-]?\d+(?:\.\d+)?)(%|秒)?", line)
                        if m:
                            key = m[1].strip()
                            val = float(m[2]) if '.' in m[2] else int(m[2])
                            unit = m[3] if m[3] else ""
                            if not unit and "時間" in key:
                                unit = "秒"

                            source = f"套裝：{source_label}"  # ✅ 直接用來源變數
                            effect_dict.setdefault((key, unit), []).append((val, source))
                            self.effect_dict_raw = effect_dict  # 取能力值暫存
                            self.update_stat_bonus_display()    # ✅ 加這行：裝備資料全部準備好後更新素質顯示

                            




                    # 原本的解析邏輯也照做
                        parsed = self.try_extract_effect(line)
                        if parsed:
                            key, value, unit = parsed
                            key = self.normalize_effect_key(key)
                            #source_label = part_name  # or 卡片名稱 or 套裝來源

                            # 建立效果來源清單
                            #effect_dict.setdefault((key, unit), []).append((value, source_label))



        #被動技能給的BUFF
        
        skillbuff_path = os.path.join("data", "skillbuff.lua")
        skillbuff_effect_dict = self.apply_skill_buffs_into_effect_dict(skillbuff_path, enabled_skill_levels, refine_inputs, get_values, grade)
        for key, entries in skillbuff_effect_dict.items():
            if key in effect_dict:
                effect_dict[key].extend(entries)
            else:
                effect_dict[key] = entries.copy()

        
        # ✅ 排序合併結果
        combined = []
        show_source = self.show_combo_source_checkbox.isChecked()
        
        sort_mode = self.sort_mode_combo.currentText()

        if sort_mode == "來源順序":
            sorted_effect_items = effect_dict.items()

        elif sort_mode == "依名稱":
            def sort_key(item):
                (key, unit) = item[0]
                return (key, unit)
            sorted_effect_items = sorted(effect_dict.items(), key=sort_key)

        elif sort_mode in custom_sort_orders:  # ✅ 通用處理
            def sort_key(item):
                (key, unit) = item[0]
                return (get_custom_sort_value(key, sort_mode), key)
            sorted_effect_items = sorted(effect_dict.items(), key=sort_key)

        else:
            sorted_effect_items = effect_dict.items()  # fallback 保底



        # 排序應用在效果總表輸出
        for (key, unit), entries in sorted_effect_items:
        



            total = sum(val for val, _ in entries)
            #print(f"[DEBUG] key={key} unit={unit} total={total}")
            if unit == "秒":
                total = round(total, 1)
                value_str = f"{total:.1f}{unit}"
            else:
                value_str = f"{total:+g}{unit}"

            if show_source:
                for val, source in entries:
                    val_str = f"{val:.1f}{unit}" if unit == "秒" else f"{val:+g}{unit}"
                    combined.append(f"{key} {val_str}  ← 〔{source}〕")
                combined.append(f"🧮{key} {value_str}  ← 〔總和〕🧮")
            else:
                combined.append(f"{key} {value_str}")
        



        #self.total_effect_text.setPlainText("\n".join(combined))
        #self.combo_effect_text.setPlainText("\n".join(combo_effects_all))
        self.total_combined_raw = combined  # 儲存未過濾的總表行
        self.safe_update_textbox(self.total_effect_text, "\n".join(combined))
        self.safe_update_textbox(self.combo_effect_text, "\n".join(combo_effects_all))
        # 不論有沒有套裝效果、裝備或技能，一律記錄 effect_dict
        self.effect_dict_raw = effect_dict
        self.update_stat_bonus_display()
        #運算
        self.replace_custom_calc_content()


        

    def trigger_total_effect_update(self):
        self.display_all_effects()
        self.update_total_effect_display()
        self.update_dex_int_half_note()


    def parse_equipment_blocks(self, content):
        import re

        blocks = {}
        pattern = re.compile(r"\[(\d+)\]\s*=\s*{", re.MULTILINE)
        matches = list(pattern.finditer(content))
        total = len(matches)
        print(f"📦 開始解析裝備區塊，共 {total} 筆資料")

        for i, match in enumerate(matches):
            item_id = int(match.group(1))
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)

            block_text = content[start:end].strip()

            # 加回完整大括號包裹，確保 block 格式正確
            block_text_full = "{" + block_text.rstrip(",") + "}"

            blocks[item_id] = block_text_full
            print(f"  → 處理中 {i+1}/{total}", end="\r")
        print(f"\n✅ 解析完成，共 {len(blocks)} 筆裝備。")
        return blocks

        
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "確認關閉",
            "確定要關閉應用程式嗎？未儲存的變更將會遺失。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    
    def load_saved_inputs(self, filename="saved_inputs.json"):


        if not os.path.exists(filename):
            return
        # 🔹 暫停所有 widget 的 signal
        for widget in self.findChildren(QWidget):
            widget.blockSignals(True)

        with open(filename, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # input_fields 的 QComboBox 或 QLineEdit
        for key, val in saved_data.items():
            if key in self.input_fields:
                field = self.input_fields[key]
                if isinstance(field, QComboBox):
                    index = field.findText(val)
                    if index != -1:
                        field.setCurrentIndex(index)
                else:
                    field.setText(val)

        # 裝備與卡片欄位
        for part, info in self.refine_inputs_ui.items():
            equip_key = f"{part}_equip"
            if equip_key in saved_data:
                info["equip"].setText(saved_data[equip_key])
            for i in range(4):
                card_key = f"{part}_card{i+1}"
                if card_key in saved_data:
                    info["cards"][i].setText(saved_data[card_key])

        #怪物相關欄位
        self.size_box.setCurrentIndex(saved_data.get("size", 0))
        self.element_box.setCurrentIndex(saved_data.get("element", 0))
        self.race_box.setCurrentIndex(saved_data.get("race", 0))
        self.class_box.setCurrentIndex(saved_data.get("class", 0))
        self.def_input.setText(saved_data.get("def", "0"))
        self.defc_input.setText(saved_data.get("defc", "0"))
        self.res_input.setText(saved_data.get("res", "0"))
        self.mdef_input.setText(saved_data.get("mdef", "0"))
        self.mdefc_input.setText(saved_data.get("mdefc", "0"))
        self.mres_input.setText(saved_data.get("mres", "0"))
        self.element_lv_input.setText(saved_data.get("element_lv", "1"))
        
        # 🔹 恢復 signal
        for widget in self.findChildren(QWidget):
            widget.blockSignals(False)
            
        # 技能欄位
        if "skill_name" in saved_data:
            index = self.skill_box.findText(saved_data["skill_name"])
            if index != -1:
                self.skill_box.setCurrentIndex(index)
        # note 欄位最後處理
        for part, info in self.refine_inputs_ui.items():
            note_key = f"{part}_note"
            if note_key in saved_data and "note" in info:
                info["note"].setPlainText(saved_data[note_key])

        
    def save_preset(self, part):
        info = self.refine_inputs_ui[part]
        name = info["preset_input"].text().strip()
        if not name:
            QMessageBox.warning(self, "錯誤", "請輸入儲存名稱")
            return
        data = {
            "equip": info["equip"].text(),
            "cards": [c.text() for c in info["cards"]],
            "note": info["note"].toPlainText(),
            "refine": info["refine"].text(),
            "grade": info["grade"].currentText()
        }

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 儲存成功後清空名稱輸入欄位
        info["preset_input"].clear()
        
        self.refresh_presets(part)

    def load_preset(self, part, preset_name):
        info = self.refine_inputs_ui[part]

        # 直接用對話框選到的 preset_name，而不是 combo.currentText()
        name = preset_name
        if not name:
            return

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        if not os.path.exists(path):
            return

        # 確認是否覆蓋
        if info["equip"].text() or any(c.text() for c in info["cards"]) or info["note"].toPlainText():
            reply = QMessageBox.question(
                self, "覆蓋確認",
                f"目前 {part} 已有資料，確定要覆蓋？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        
        info["preset_input"].setText(preset_name)#讀取檔名傳入名稱
        
        info["equip"].setText(data.get("equip", ""))
        for i in range(4):
            info["cards"][i].setText(data.get("cards", [""]*4)[i])
        info["note"].setPlainText(data.get("note", ""))

        # ✅ 這些也是保留
        info["refine"].setText(data.get("refine", "0"))
        grade = data.get("grade", "N")
        index = info["grade"].findText(grade)
        if index >= 0:
            info["grade"].setCurrentIndex(index)

        self.display_item_info()


    def delete_preset(self, part, name):
        if not name:
            return

        path = os.path.join(self.preset_folder, f"{part}_{name}.json")
        if os.path.exists(path):
            os.remove(path)

        # 刪掉後刷新一下清單（現在只是回傳清單，不會更新 combo）
        self.refresh_presets(part)


    def refresh_presets(self, part):
        files = os.listdir(self.preset_folder)
        names = [
            f[len(part)+1:-5]
            for f in files
            if f.startswith(part + "_") and f.endswith(".json")
        ]
        return sorted(names)

    def open_save_manager(self, part_name):
        save_list = self.refresh_presets(part_name)
        dialog = SaveManagerDialog(part_name, save_list, self.delete_preset, self)

        # 取得按鈕的螢幕座標
        button = self.refine_inputs_ui[part_name]["manage_btn"]
        global_pos = button.mapToGlobal(QPoint(0, 0))

        # 預設：放在按鈕右側
        x = global_pos.x() + button.width() + 10
        y = global_pos.y()

        # 取得母視窗範圍（相對螢幕的座標）
        parent_geom = self.geometry()
        parent_x, parent_y = parent_geom.x(), parent_geom.y()
        parent_width, parent_height = parent_geom.width(), parent_geom.height()

        # 對話框大小（已固定 300x400）
        dialog_width, dialog_height = dialog.width(), dialog.height()

        # ✅ 限制在母視窗範圍內
        if x + dialog_width > parent_x + parent_width:
            x = global_pos.x() - dialog_width - 50
        if y + dialog_height > parent_y + parent_height:
            y = parent_y + parent_height - dialog_height - 50
        if y < parent_y:  # 不要超出上邊界
            y = parent_y + 10

        # 移動到最終位置
        dialog.move(x, y)

        if dialog.exec():
            selected = dialog.selected_save
            if selected:
                self.load_preset(part_name, selected)










    def apply_selected_equip(self):

        if not self.current_edit_part:
            print("❌ 沒有選擇編輯部位")
            return

        selected_item = self.name_field.text().strip()
        if not selected_item:
            print("⚠️ 沒有選擇要套用的裝備")
            return

        part_name, field_type = self.current_edit_part.split(" - ")

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 無法辨識部位：{part_name}")
            return

        ui = self.refine_inputs_ui[part_name]

        if field_type == "裝備":
            ui["equip"].setText(selected_item)
        elif field_type.startswith("卡片"):
            try:
                card_index = int(field_type[-1]) - 1
                if 0 <= card_index < 4:
                    ui["cards"][card_index].setText(selected_item)
                else:
                    print(f"❌ 卡片編號錯誤：{field_type}")
            except ValueError:
                print(f"❌ 無法解析卡片編號：{field_type}")
        else:
            print(f"❌ 不支援欄位類型：{field_type}")
            return
        

        # 最後刷新畫面
        
        self.display_item_info()

    def apply_result_to_note(self):

        if not self.current_edit_part:
            print("❌ 沒有選擇編輯部位")
            return

        part_name, field_type = self.current_edit_part.split(" - ")
        print(f"目前部位:{part_name} 位置:{field_type}")
        if field_type != "詞條":
            print("⚠️ 當前非詞條欄 ，無法套用語法")
            return

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 無法辨識部位：{part_name}")
            return

        note_widget = self.refine_inputs_ui[part_name].get("note")
        if note_widget:
            new_text = self.result_output.toPlainText().strip()
            note_widget.setPlainText(new_text)
            print(f"✅ 已將語法套用至「{part_name}」詞條欄")
        else:
            print(f"❌ 找不到 {part_name} 的詞條欄位")
        
        # 最後刷新畫面
        self.display_item_info()




    def clear_selected_field(self):
        if not self.current_edit_part:
            print("❌ 沒有選擇編輯欄位")
            return

        part_name, field_type = self.current_edit_part.split(" - ")

        if part_name not in self.refine_inputs_ui:
            print(f"❌ 找不到部位：{part_name}")
            return

        ui = self.refine_inputs_ui[part_name]

        if field_type == "裝備":
            ui["equip"].clear()

        elif field_type.startswith("卡片"):
            try:
                idx = int(field_type[-1]) - 1
                if 0 <= idx < 4:
                    ui["cards"][idx].clear()
                else:
                    print("❌ 卡片欄位編號超出範圍")
            except ValueError:
                print("❌ 卡片欄位解析失敗")

        elif field_type == "詞條":
            if "note" in ui:
                ui["note"].clear()
            else:
                print(f"❌ 找不到詞條欄位於：{part_name}")

        else:
            print(f"❌ 不支援的欄位類型：{field_type}")
            return

        self.display_item_info()
        if field_type == "詞條":
            self.result_output.clear()

    def save_compare_base(self):
        self.auto_compare_checkbox.setChecked(False)
        self.replace_custom_calc_content()#儲存前強制運算
        text = self.custom_calc_box.toPlainText()
        with open("compare_base.txt", "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "儲存成功", "已儲存目前數據作為比對基準。")
        self.auto_compare_checkbox.setChecked(True)

    def compare_with_base(self):
        import re

        def parse_block(text):
            d = {}
            for line in text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().replace(",", "")
                    num = re.findall(r"[-]?\d+\.?\d*", val)
                    if num:
                        d[key.strip()] = val
            return d

        try:
            with open("compare_base.txt", "r", encoding="utf-8") as f:
                base_text = f.read()
        except FileNotFoundError:
            QMessageBox.warning(self, "錯誤", "找不到比對基準，請先儲存。")
            return

        current_text = self.custom_calc_box.toPlainText()
        base = parse_block(base_text)
        current_lines = current_text.splitlines()

        def format_number(val_str):
            val = float(re.findall(r"[-]?\d+\.?\d*", val_str)[0])
            suffix = "%" if "%" in val_str else ""
            if val.is_integer():
                return f"{int(val):,}{suffix}"
            else:
                return f"{val:.2f}{suffix}"
                
        skip_compare_keys = {"技能公式", "技能說明"}  # 可加更多你不想比對的 key
        
        new_output = []
        for line in current_lines:
            if ":" not in line:
                new_output.append(line)
                continue

            key_part, val_part = line.split(":", 1)
            key = key_part.strip()
            val_clean = val_part.strip().replace(",", "")
            
            if key in skip_compare_keys:
                new_output.append(line)  # 直接加入不比對
                continue

            if key in base:
                try:
                    old_val_str = base[key]
                    new_val_str = val_clean

                    old_val = float(re.findall(r"[-]?\d+\.?\d*", old_val_str)[0])
                    new_val = float(re.findall(r"[-]?\d+\.?\d*", new_val_str)[0])

                    if old_val != new_val:
                        diff = new_val - old_val
                        sign = "+" if diff > 0 else "-"
                        suffix = "%" if "%" in new_val_str else ""
                        old_fmt = format_number(old_val_str)
                        new_fmt = format_number(new_val_str)

                        # 總傷害顯示百分比與差額
                        if "傷害" in key:
                            percent_val = abs(diff / old_val * 100)
                            diff_fmt = f"{sign}{int(abs(diff)):,} / {sign}{percent_val:.2f}%"
                            
                        elif "技能倍率" in key:
                            percent_val = abs(diff / old_val * 100)
                            diff_fmt = f"{sign}{int(abs(diff)):,}{suffix} / {sign}{percent_val:.2f}%"

                        else:
                            diff_fmt = f"{sign}{abs(diff):.0f}{suffix}"

                        arrow_str = f"{old_fmt} → {new_fmt}"
                        # 保留前綴與原有空格
                        prefix = line[:line.index(":") + 1]
                        suffix_space = val_part[:len(val_part) - len(val_part.lstrip())]
                        # 調整：括號前留 2 空格
                        new_line = f"{prefix}{suffix_space}{arrow_str}  ({diff_fmt})"
                        new_output.append(new_line)
                    else:
                        new_output.append(line)
                except Exception as e:
                    new_output.append(f"{line}  ⛔錯誤: {e}")

            else:
                new_output.append(line)

        self.custom_calc_box.setHtml(self.generate_highlighted_html(new_output))

        #self.custom_calc_box.setPlainText("\n".join(new_output))


    def dataloading(self):
        self.current_file = None  # 尚未開啟任何檔案
        lub_path = r"C:\Program Files (x86)\Gravity\RagnarokOnline\System\iteminfo_new.lub"
        lua_output = r"data/iteminfo_new.lua"

        # 如果 lua 檔案不存在，就執行反編譯
        if not os.path.exists(lua_output):
            print(f"⚠️ 找不到 {lua_output}，開始反編譯 {lub_path} ...")
            if not decompile_lub(lub_path, lua_output):
                print("❌ 反編譯失敗，無法繼續")
                return
        else:
            print(f"✅ 找到 {lua_output}，跳過反編譯")

        # 讀取資料
        self.parsed_items = parse_lub_file(lua_output)#讀取物品名稱

        import shutil
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        equipment_lua_path = "data/EquipmentProperties.lua"
        # === 設定路徑 ===
        GRFCL_EXE = os.path.join(BASE_DIR, "APP", "GrfCL.exe")
        GRF_PATH = r"C:\Program Files (x86)\Gravity\RagnarokOnline\data.grf"
        UNLUAC_JAR = os.path.join(BASE_DIR, "APP", "unluac.jar")
        INPUT_FILE = os.path.join(BASE_DIR, "data", "LuaFiles514", "Lua Files", "EquipmentProperties", "EquipmentProperties.lub")
        OUTPUT_FOLDER = os.path.join(BASE_DIR, "data")
        OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "EquipmentProperties.lua")


        # === 從 GRF 解壓 LUB ===
        def extract_lub_from_grf():
            #print("🔍 檢查 GRFCL_EXE 實際路徑：", GRFCL_EXE)
            #print("🔍 存在嗎？", os.path.exists(GRFCL_EXE))
            if not os.path.exists(GRFCL_EXE):
                print(f" 找不到 GrfCL.exe：{GRFCL_EXE}")
                return False

            print(" 正在從 GRF 解壓 LUB 檔...")
            result = subprocess.run([
                GRFCL_EXE,
                "-open", GRF_PATH,
                "-extractFolder", ".",
                "data\\LuaFiles514\\Lua Files\\EquipmentProperties\\EquipmentProperties.lub",
                "-exit"
            ], cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            #print("stdout:", result.stdout)
            #print("stderr:", result.stderr)

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

        if not os.path.exists(equipment_lua_path):
            print("⚠️ 找不到 EquipmentProperties.lua，執行 convert_lub_to_lua.py 生成...")
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
                print("✅ EquipmentProperties.lua 已成功生成")
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))

                temp_folder = os.path.join(base_dir, "data", "LuaFiles514")
                if os.path.exists(temp_folder):
                    try:
                        shutil.rmtree(temp_folder)
                        print(f"✅ 已刪除暫存資料夾")
                    except Exception as e:
                        print(f"⚠️ 刪除暫存資料夾失敗：{e}")
                else:
                    print(f"⚠️ 找不到暫存資料夾：{temp_folder}")
        else:
            print("✅ 找到 EquipmentProperties.lua，跳過編譯處理")


        # 載入 EquipmentProperties.lub
        
        with open(r"data/EquipmentProperties.lua", "r", encoding="utf-8") as f:
            content = f.read()
        self.equipment_data = self.parse_equipment_blocks(content)
        
        return self.parsed_items
    
    def __init__(self):
        
        #self.dataloading()#讀取並載入物品跟裝備能力
        
        super().__init__()
        self.setWindowTitle("RO物品查詢計算工具")
        self.current_edit_part = None  # 用來記錄目前正在編輯的部位名稱

        self.preset_folder = "equip_presets"
        os.makedirs(self.preset_folder, exist_ok=True)



        
        # UI 元件初始化


        self.parsed_items = {}#預先初始化
        self.current_file = None # 尚未開啟任何檔案
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("輸入物品編號、名稱或內容...")
        
        self.search_input.textChanged.connect(self.update_combobox)

        self.result_box = QComboBox()
        self.result_box.currentIndexChanged.connect(self.display_item_info)

        self.name_field = QLineEdit()
        self.name_field.setReadOnly(True)

        self.kr_name_field = QLineEdit()
        self.kr_name_field.setReadOnly(True)

        self.slot_field = QLineEdit()
        self.slot_field.setReadOnly(True)

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)

        self.equip_text = QTextEdit()
        self.equip_text.setReadOnly(True)

        self.sim_effect_label = QLabel("效果解析")
        #self.sim_effect_text = QTextEdit()
        #self.sim_effect_text.setReadOnly(True)
        




        # 建立輸入欄位
        self.input_fields = {}

        self.stat_fields = {
            "BaseLv": 11, "JobLv": 12, "JOB": 19, 
            "STR": 32, "AGI": 33, "VIT": 34, "INT": 35, "DEX": 36, "LUK": 37,
            "POW": 255, "STA": 256, "WIS": 257, "SPL": 258, "CON": 259, "CRT": 260,"石碑開啟格數": 263 ,"石碑精煉": 264
            
        }

        self.refine_parts = {
            # === 裝備部位 ===
            "頭上":   {"slot": 10, "type": "裝備"},
            "頭中":   {"slot": 11, "type": "裝備"},
            "頭下":   {"slot": 12, "type": "裝備"},
            "鎧甲":   {"slot": 2,  "type": "裝備"},
            "右手(武器)":   {"slot": 4,  "type": "裝備"},
            "左手(盾牌)":   {"slot": 3,  "type": "裝備"},
            "披肩":   {"slot": 5,  "type": "裝備"},
            "鞋子":   {"slot": 6,  "type": "裝備"},
            "飾品右": {"slot": 7,  "type": "裝備"},
            "飾品左": {"slot": 8,  "type": "裝備"},

            # === 影子裝備 ===
            "影子鎧甲":   {"slot": 30, "type": "影子"},
            "影子手套":   {"slot": 31, "type": "影子"},
            "影子盾牌":     {"slot": 32, "type": "影子"},
            "影子鞋子":   {"slot": 33, "type": "影子"},
            "影子耳環右": {"slot": 34, "type": "影子"},
            "影子墬子左": {"slot": 35, "type": "影子"},

            # === 服飾部位 ===
            "服飾頭上":   {"slot": 41, "type": "服飾"},
            "服飾頭中":   {"slot": 42, "type": "服飾"},
            "服飾頭下":   {"slot": 43, "type": "服飾"},
            "服飾斗篷":   {"slot": 44, "type": "服飾"},
            
            # === 石碑/寵物部位 ===
            "符文石碑":   {"slot": 100, "type": "石碑"},
            "寵物蛋":   {"slot": 101, "type": "寵物"},
        }
        def get_part_slot_from_source(source_str):
            for part_name, info in self.refine_parts.items():
                if part_name in source_str:
                    return info["slot"]
            return 9999  # 未知來源排最後

        # 三欄主視窗布局
        main_layout = QHBoxLayout()
        
        # ===== 左側：角色能力與裝備分頁 =====
        # 1. 建立分頁元件
        tab_widget = QTabWidget()
        tab_widget.setFixedWidth(340)
        # 2. 為每個分頁建立 ScrollArea → 放內容
        # === 分頁1：角色能力值 ===
        char_scroll = QScrollArea()
        char_scroll.setWidgetResizable(True)
        char_inner = QWidget()
        char_layout = QVBoxLayout(char_inner)
        char_scroll.setWidget(char_inner)
        char_layout.addWidget(QLabel("角色能力值"))
        # 儲存加成顯示欄位
        self.stat_bonus_labels = {}

        for label, gid in self.stat_fields.items():
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignLeft)
            row_label = QLabel(label)
            row_label.setFixedWidth(50)  # 可自行調整寬度
            row_layout.addWidget(row_label)
            
            if label == "JOB":
                combo = QComboBox()
                for job_id, job_info in sorted(job_dict.items()):
                    combo.addItem(job_info["name"], job_id)
                combo.currentIndexChanged.connect(self.trigger_total_effect_update)
                combo.setMaximumWidth(210)#調整寬度
                self.input_fields[label] = combo
                row_layout.addWidget(combo)
            else:
                field = QLineEdit()
                field.setPlaceholderText(f"{label} (get({gid}))")
                field.textChanged.connect(self.trigger_total_effect_update)
                field.setMaximumWidth(50)#調整寬度
                self.input_fields[label] = field
                row_layout.addWidget(field)
                
                stat_names = ["STR", "AGI", "VIT", "INT", "DEX", "LUK", "POW", "STA", "WIS", "SPL", "CON", "CRT"]#ROCalculator
                if label in stat_names:
                    bonus_label = QLabel("= ?")
                    bonus_label.setFixedWidth(160)
                    bonus_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    row_layout.addWidget(bonus_label)
                    self.stat_bonus_labels[label] = bonus_label
                
                if label == "JobLv":
                    bonus_label = QLabel("(預留，目前無作用。)")
                    row_layout.addWidget(bonus_label)

                # ✅ 如果是 BaseLv，就加一個 QLabel 顯示素質點
                if label == "BaseLv":
                    self.stat_point_label = QLabel("（素質點：-）")
                    self.stat_point_label.setFixedWidth(180)
                    row_layout.addWidget(self.stat_point_label)

                    def update_stat_point():#取自ROCalculator
                        try:
                            lv = int(self.input_fields["BaseLv"].text())
                        except:
                            self.stat_point_label.setText("（素質點：-）")
                            return

                        is_trans = True  # 預留判斷 現在是轉生後4轉職業
                        total_pts = calculate_stat_points(lv, is_trans)

                        used_pts = sum([
                            raising_stats(self.input_fields["STR"].text()),
                            raising_stats(self.input_fields["AGI"].text()),
                            raising_stats(self.input_fields["VIT"].text()),
                            raising_stats(self.input_fields["INT"].text()),
                            raising_stats(self.input_fields["DEX"].text()),
                            raising_stats(self.input_fields["LUK"].text())
                        ])
                        remain_pts = total_pts - used_pts
                        total_tpts = get_total_tstat_points(lv)
                        tstat_used = self.calculate_tstat_total_used()
                        tstat_remain = total_tpts - tstat_used

                        #self.stat_point_label.setText(f"（素質點：{total_pts} / 已用 {used_pts} / 剩餘 {remain_pts}｜特性點：{total_tpts} / 已用 {tstat_used} / 剩餘 {tstat_remain}）")
                        self.stat_point_label.setText(f"剩餘素質 {remain_pts}｜特性 {tstat_remain}")
                    # ❗ BaseLv 輸入時更新
                    field.textChanged.connect(update_stat_point)
                    self._update_stat_point_callback = update_stat_point  # ✅ 暫存回呼
                 # 🟣 隱藏「石碑」相關欄位
                if label in ["石碑開啟格數", "石碑精煉"]:
                    row_label.setVisible(False)
                    field.setVisible(False)
                    continue  # 不需要顯示在角色能力區     

            
            char_layout.addLayout(row_layout)
            char_layout.setAlignment(Qt.AlignTop)
        # === 計算素質無詠 ===
        
        self.DEX_INT_265_label = QLabel("無詠計算位置")
        #self.DEX_INT_265_label.setFont(QFont("Consolas", 12))
        #self.DEX_INT_265_label.setFixedWidth(50)
        #self.DEX_INT_265_label.setAlignment(Qt.AlignRight)
        char_layout.addWidget(self.DEX_INT_265_label)


        tab_widget.addTab(char_scroll, "角色能力值")
        
        # === 分頁2：裝備設定 ===
        equip_scroll = QScrollArea()
        equip_scroll.setWidgetResizable(True)
        equip_inner = QWidget()
        equip_layout = QVBoxLayout(equip_inner)
        equip_scroll.setWidget(equip_inner)


        equip_layout.addWidget(QLabel("裝備與卡片設定"))

        self.refine_inputs_ui = {}
        visible_types = ["裝備", "影子", "服飾", "石碑", "寵物"]

        for part_name, info in self.refine_parts.items():
            if info["type"] not in visible_types:
                continue

            slot_id = info["slot"]
            
            def make_focus_func_focus(part_label, input_field, label_name):
                def focus(event):
                    self.clear_current_edit()

                    self.current_edit_part = f"{part_label} - {label_name}"
                    self.current_edit_label.setText(f"目前部位：{part_label} - {label_name}")
                    self.unsync_button.setVisible(True)
                    self.unsync_button2.setVisible(True)
                    self.apply_to_note_button.setVisible(True)
                    self.clear_field_button2.setVisible(True)
                    self.apply_equip_button.setVisible(True)
                    self.clear_field_button.setVisible(True)
                    
                    self.set_edit_lock(part_label, label_name)
                    input_field.setStyleSheet("background-color: #ff0000;")  # 紅
                    self.search_input.setFocus()  # ✅ 把焦點移到搜尋欄
                    # ✅ 若不是詞條，就切回裝備查詢分頁
                    if label_name != "note":
                        self.tab_widget.setCurrentIndex(self.search_tab_index)

                    # ✅ 只有左邊欄位有文字時才清空搜尋欄位
                    if input_field.text().strip():
                        self.search_input.setText("")

                    text = input_field.text().strip()
                    if text:
                        # 搜尋對應的物品 ID
                        for idx in range(self.result_box.count()):
                            item_id = self.result_box.itemData(idx)
                            item = self.filtered_items.get(item_id)
                            if item and item["name"] == text and item_id in self.equipment_data:

                                self.result_box.setCurrentIndex(idx)
                                break


                    QLineEdit.mousePressEvent(input_field, event)
                return focus
                
            

            part_label = QLabel(part_name)
            equip_layout.addWidget(part_label)

            part_ui = {}
            equip_row_layout = QHBoxLayout()
            
                                    # ▶️ 儲存 / 載入 / 下拉 / 刪除控制列
            preset_row = QHBoxLayout()

            preset_name_input = QLineEdit()
            preset_name_input.setPlaceholderText("輸入儲存名稱")
            preset_name_input.setFixedWidth(160)

            save_btn = QPushButton("儲存")
            save_btn.setFixedWidth(40)
            save_btn.clicked.connect(lambda _, p=part_name: self.save_preset(p))

            #preset_combo = QComboBox()
            #preset_combo.setFixedWidth(100)
            #preset_combo.currentIndexChanged.connect(lambda _, p=part_name: self.load_preset(p))
            manage_btn = QPushButton("讀取裝備")
            manage_btn.clicked.connect(lambda _, p=part_name: self.open_save_manager(p))
            part_ui["manage_btn"] = manage_btn


            #delete_btn = QPushButton("刪除")
            #delete_btn.setFixedWidth(40)
            #delete_btn.clicked.connect(lambda _, p=part_name: self.delete_preset(p))

            preset_row.addWidget(preset_name_input)
            preset_row.addWidget(save_btn)
            #preset_row.addWidget(preset_combo)
            #preset_row.addWidget(delete_btn)
            preset_row.addWidget(manage_btn)

            equip_layout.addLayout(preset_row)

            # 保存元件供操作
            part_ui["preset_input"] = preset_name_input
            #part_ui["preset_combo"] = preset_combo

            # ▶️ 裝備欄位 + 清空
            equip_input = QLineEdit()
            equip_input.setReadOnly(True)
            if part_name == "符文石碑":
                equip_input.setPlaceholderText("石碑名稱")
            elif part_name == "寵物蛋":
                equip_input.setPlaceholderText("寵物名稱")
            else:
                equip_input.setPlaceholderText("裝備名稱")

            equip_input.setMinimumWidth(100)
            equip_input.mousePressEvent = make_focus_func_focus(part_name, equip_input, "裝備")

            clear_equip_btn = QPushButton("清空")
            clear_equip_btn.setFixedWidth(40)
            clear_equip_btn.clicked.connect(self.clear_global_state)
            clear_equip_btn.clicked.connect(lambda _, field=equip_input: [field.clear(), self.display_item_info()])
            
            equip_row_layout.addWidget(equip_input)
            equip_row_layout.addWidget(clear_equip_btn)
            part_ui["equip"] = equip_input

            # ▶️ 精煉欄位
            refine_input = QLineEdit()
            refine_input.setPlaceholderText("精煉")
            refine_input.setMaximumWidth(40)
            refine_input.setText('0')
            refine_input.textChanged.connect(self.display_item_info)
            equip_row_layout.addWidget(refine_input)
            part_ui["refine"] = refine_input
            self.input_fields[part_name] = refine_input

            # ▶️ 階級下拉
            grade_combo = QComboBox()
            if part_name == "符文石碑":
                grade_combo.addItems(["0", "1", "2", "3", "4", "5", "6" ])
                grade_combo.setMaximumWidth(50)
            elif part_name == "寵物蛋":
                grade_combo.addItems(["非常陌生", "稍微陌生", "普通", "稍微親密", "非常親密"])
                grade_combo.setMaximumWidth(95)
            else:
                grade_combo.addItems(["N", "D", "C", "B", "A"])
                grade_combo.setMaximumWidth(50)
            grade_combo.currentIndexChanged.connect(self.display_item_info)
            equip_row_layout.addWidget(grade_combo)
            part_ui["grade"] = grade_combo
            self.input_fields[f"{part_name}_階級"] = grade_combo

            # 🟢 特例：符文石碑 → 同步階級與精煉到 stat_fields

            if part_name == "符文石碑":

                def sync_stone_slots_delayed():
                    val_field = self.refine_inputs_ui["符文石碑"]["grade"]
                    grade_text = val_field.currentText().strip()
                    try:
                        grade_val = int(grade_text)
                    except ValueError:
                        grade_val = val_field.currentIndex()

                    stone_slot_field = self.input_fields.get("石碑開啟格數")
                    if stone_slot_field:
                        stone_slot_field.blockSignals(True)
                        stone_slot_field.setText(str(grade_val))
                        stone_slot_field.blockSignals(False)
                    self.trigger_total_effect_update()
                    
                def sync_stone_slots(*_):
                    # 🔹 延遲一個事件循環再執行，確保取到更新後的值
                    QTimer.singleShot(0, sync_stone_slots_delayed)

                def sync_stone_refine():
                    val_field = self.refine_inputs_ui["符文石碑"]["refine"]
                    text_val = val_field.text().strip()
                    try:
                        val = int(text_val)
                    except ValueError:
                        val = 0

                    stone_refine_field = self.input_fields.get("石碑精煉")
                    if stone_refine_field:
                        stone_refine_field.blockSignals(True)
                        stone_refine_field.setText(str(val))
                        stone_refine_field.blockSignals(False)
                    self.trigger_total_effect_update()

                grade_combo.currentIndexChanged.connect(sync_stone_slots)
                refine_input.textChanged.connect(sync_stone_refine)


            # ▶️ 將裝備行 layout 加進主 layout
            equip_layout.addLayout(equip_row_layout)

            # ▶️ 卡片欄位們 + 清空按鈕
            card_inputs = []
            for i in range(4):
                card_row_layout = QHBoxLayout()
                card_row_layout.setSpacing(0)
                card_row_layout.setContentsMargins(0, 0, 0, 0)
                card_input = QLineEdit()
                
                card_input.setReadOnly(True)
                card_input.setPlaceholderText(f"卡片 {i+1}")
                card_input.mousePressEvent = make_focus_func_focus(part_name, card_input, f"卡片{i+1}")

                clear_card_btn = QPushButton("清空")
                clear_card_btn.setFixedWidth(40)
                clear_card_btn.clicked.connect(self.clear_global_state)
                clear_card_btn.clicked.connect(lambda _, field=card_input: [field.clear(), self.display_item_info()])
                
                card_row_layout.addWidget(card_input)
                card_row_layout.addWidget(clear_card_btn)

                # 把卡片欄整行加進主裝備 layout
                card_container = QWidget()
                card_container.setLayout(card_row_layout)
                equip_layout.addWidget(card_container)

                card_inputs.append(card_input)
                


            # ▶️ 詞條欄位（多行文字）+ 清空
            note_text = QTextEdit()
            note_text.setPlaceholderText("lua函數")
            note_text.setObjectName(f"{part_name}-函數")  # 例如 "頭上-詞條"
            note_text.setFixedSize(260, 20)  # ✅ 固定寬與高（寬度固定在300）
            note_text.setContentsMargins(0, 0, 0, 0)
            note_text.setReadOnly(True) 
            note_text.setVisible(False)
            note_text.textChanged.connect(self.on_function_text_changed)

            note_text_ui = QTextEdit()
            note_text_ui.setPlaceholderText("自訂詞條效果")
            note_text_ui.setObjectName(f"{part_name}-詞條")  # 例如 "頭上-詞條"
            note_text_ui.setFixedSize(260, 20)  # ✅ 固定寬與高（寬度固定在300）
            note_text_ui.setContentsMargins(0, 0, 0, 0)
            note_text_ui.setReadOnly(True) 
            note_text_ui.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            note_text_ui.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            note_text_ui.mousePressEvent = lambda event, p=part_name, w=note_text_ui , u=note_text: self.handle_note_text_clicked(event, p, w , u)
            

            
            clear_note_btn = QPushButton("清空")
            clear_note_btn.setFixedWidth(40)
            clear_note_btn.clicked.connect(self.clear_global_state)
            clear_note_btn.clicked.connect(lambda _, field=note_text: [field.clear() ,self.display_item_info()])
            
            
            note_row_layout = QHBoxLayout()
            note_row_layout.setContentsMargins(0, 0, 0, 0)
            note_row_layout.setSpacing(5)
            note_row_layout.addWidget(note_text)
            note_row_layout.addWidget(note_text_ui)
            note_row_layout.addWidget(clear_note_btn)

            note_container = QWidget()
            note_container.setLayout(note_row_layout)
            note_container.setFixedWidth(300)  # ✅ 包裹容器也設定固定寬度

            equip_layout.addWidget(note_container)
            
            

            part_ui["note"] = note_text  # ✅ 儲存以便之後取用
            part_ui["cards"] = card_inputs
            part_ui["note_ui"] = note_text_ui
            
            

            self.refine_inputs_ui[part_name] = part_ui
            self.refresh_presets(part_name)

            # 🟢 特例：符文石碑 → 隱藏卡片與詞條欄位
            if part_name in ("符文石碑", "寵物蛋"):
                # 隱藏卡片欄位
                for c in part_ui["cards"]:
                    c.setVisible(False)
                    parent_layout = c.parentWidget()
                    if parent_layout:
                        parent_layout.setVisible(False)

                # 隱藏詞條區
                if "note" in part_ui:
                    part_ui["note"].setVisible(False)
                if "note_ui" in part_ui:
                    part_ui["note_ui"].setVisible(False)
                note_widget = part_ui["note"].parentWidget()
                if note_widget:
                    note_widget.setVisible(False)

                # 🧩 若是寵物蛋，再隱藏精煉欄位
                if part_name == "寵物蛋" and "refine" in part_ui:
                    refine_widget = part_ui["refine"]
                    refine_widget.setVisible(False)
                    refine_parent = refine_widget.parentWidget()
                    if refine_parent:
                        refine_widget.hide()  # 雙保險：同時呼叫 hide()








        tab_widget.addTab(equip_scroll, "裝備設定")
        main_layout.addWidget(tab_widget, 2)
        

        # === 新增技能分頁（含搜尋） ===
        skill_page = QWidget()
        skill_layout = QVBoxLayout(skill_page)

        # 搜尋欄位
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜尋技能/料理：")
        self.skill_search_bar = QLineEdit()
        self.skill_search_bar.setPlaceholderText("輸入技能/料理名稱...")
        self.skill_search_bar.textChanged.connect(self.filter_skill_list)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.skill_search_bar)
        skill_layout.addLayout(search_layout)

        # 技能清單區塊（可滾動）
        self.skill_checkbox_area = QWidget()
        self.skill_checkbox_layout = QVBoxLayout(self.skill_checkbox_area)
        self.skill_checkbox_layout.setAlignment(Qt.AlignTop)

        self.skill_checkboxes = {}
        for name, data in all_skill_entries.items():
            checkbox = QCheckBox(f"{data['type']} {name}")
            checkbox.stateChanged.connect(self.trigger_total_effect_update)
            self.skill_checkboxes[name] = checkbox
            self.skill_checkbox_layout.addWidget(checkbox)
            

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.skill_checkbox_area)

        # ✅ 讓技能清單填滿底部空間
        skill_layout.addWidget(scroll, stretch=1)

        # 加入主分頁
        tab_widget.addTab(skill_page, "增益技能/料理")

        





        # ===== 中間：裝備查詢區塊 =====
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        # 建立 TabWidget
        self.tab_widget = QTabWidget()

        # ====== 原本裝備查詢頁 ======
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        # ...原本裝備查詢內容塞進 middle_layout...
        middle_scroll = QScrollArea()
        middle_scroll.setWidgetResizable(True)
        middle_scroll.setWidget(middle_widget)
        middle_scroll.setFixedWidth(500)

        equip_tab = QWidget()
        equip_layout = QVBoxLayout(equip_tab)
        equip_layout.addWidget(middle_scroll)
        self.search_tab_index = self.tab_widget.addTab(equip_tab, "裝備查詢")


        # ▶️ 編輯狀態 + 解除同步按鈕 + 全域精煉選單
        edit_status_layout = QHBoxLayout()
        self.current_edit_label = QLabel("目前部位：")
        self.unsync_button = QPushButton("🔓解除鎖定")
        self.unsync_button.setVisible(False)
        self.unsync_button.clicked.connect(self.clear_global_state)
        self.unsync_button.clicked.connect(self.clear_current_edit)
        # ▶️ 套用按鈕
        self.apply_equip_button = QPushButton("套用")
        self.apply_equip_button.clicked.connect(self.clear_global_state)
        self.apply_equip_button.clicked.connect(self.apply_selected_equip)        
        self.apply_equip_button.setVisible(False)
        
        self.clear_field_button = QPushButton("清空")
        self.clear_field_button.clicked.connect(self.clear_global_state)
        self.clear_field_button.clicked.connect(self.clear_selected_field)        
        self.clear_field_button.setVisible(False)


        # ✅ 全域精煉與階級欄位
        self.global_refine_input = QLineEdit()
        self.global_refine_input.setPlaceholderText("全域精煉")
        self.global_refine_input.setMaximumWidth(40)

        self.global_grade_combo = QComboBox()
        self.global_grade_combo.addItems(["N", "D", "C", "B", "A"])
        self.global_grade_combo.setMaximumWidth(50)
        self.global_refine_input.textChanged.connect(self.display_item_info)
        self.global_grade_combo.currentIndexChanged.connect(self.display_item_info)

        # 預設隱藏（只有在未編輯狀態時顯示）
        self.global_refine_input.setVisible(True)
        self.global_grade_combo.setVisible(True)

        
        # 擺進橫向排版
        edit_status_layout.addWidget(self.current_edit_label)
        edit_status_layout.addWidget(self.clear_field_button)
        edit_status_layout.addWidget(self.apply_equip_button)
        edit_status_layout.addWidget(self.unsync_button)
        edit_status_layout.addWidget(self.global_refine_input)
        edit_status_layout.addWidget(self.global_grade_combo)

        middle_layout.addLayout(edit_status_layout)
        def add_labeled_row(layout, label_text, widget, label_width=80):
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(label_width)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(label)
            row.addWidget(widget)
            layout.addLayout(row)

        # 使用函式新增橫向排列項目
        add_labeled_row(middle_layout, "查詢關鍵字", self.search_input)
        add_labeled_row(middle_layout, "符合項目", self.result_box)
        #add_labeled_row(middle_layout, "中文名稱", self.name_field)
        #add_labeled_row(middle_layout, "韓文名稱", self.kr_name_field)
        #add_labeled_row(middle_layout, "鑲嵌孔數", self.slot_field)
        #middle_layout.addWidget(QLabel("物品說明"))
        middle_layout.addWidget(self.desc_text)
        self.btn_recompile = QPushButton("重新編譯(需先更新RO主程式。)")
        self.btn_recompile.clicked.connect(self.recompile)
        middle_layout.addWidget(self.btn_recompile)
        #self.btn_recompile.setVisible(False)#重新編譯先隱藏
        
       

        # ====== 技能指令分頁 ======
        function_tab = QWidget()
        function_layout = QVBoxLayout(function_tab)

        # 建立第1個橫向 layout（標籤 + 解鎖）
        edit_function_layout = QHBoxLayout()

        self.function_selector = QComboBox()
        self.function_selector.setMaximumWidth(200)
        self.update_function_selector()

        self.se_function = QLabel("選擇函數：")
        self.unsync_button2 = QPushButton("🔓解除鎖定")
        self.unsync_button2.setVisible(False)
        self.unsync_button2.clicked.connect(self.clear_global_state)
        self.unsync_button2.clicked.connect(self.clear_current_edit)
        self.apply_to_note_button = QPushButton("套用到詞條")
        self.apply_to_note_button.setVisible(False)
        self.apply_to_note_button.clicked.connect(self.clear_global_state)
        self.apply_to_note_button.clicked.connect(self.apply_result_to_note)
        

        
        self.clear_field_button2 = QPushButton("清空")
        self.clear_field_button2.clicked.connect(self.clear_global_state)
        self.clear_field_button2.clicked.connect(self.clear_selected_field)
        
        self.clear_field_button2.setVisible(False)

        # 🔍 建立全域技能搜尋欄位（放在你想要的位置）
        self.skill_search_input = QLineEdit()
        self.skill_search_input.setPlaceholderText("🔍 搜尋技能")
        self.skill_search_input.setVisible(False)
        
        
        edit_function_layout.addWidget(self.se_function)
        edit_function_layout.addWidget(self.skill_search_input)
        edit_function_layout.addWidget(self.clear_field_button2)
        edit_function_layout.addWidget(self.apply_to_note_button)

        edit_function_layout.addWidget(self.unsync_button2)
        function_layout.addLayout(edit_function_layout)

        # ✅ 建立第2個橫向 layout（函數選單 + 參數欄位）
        edit_function_layout2 = QHBoxLayout()  # 你漏了這行

        edit_function_layout2.addWidget(self.function_selector)


        # ✅ 參數區改用 HBoxLayout
        self.param_layout = QHBoxLayout()
        self.param_widgets = []
        edit_function_layout2.addLayout(self.param_layout)

        function_layout.addLayout(edit_function_layout2)

        
        # 按鈕
        self.gen_button = QPushButton("產生")
        function_layout.addWidget(self.gen_button)
        # 結果輸出
        self.result_output = QTextEdit()
        #self.result_output.setReadOnly(True)
        function_layout.addWidget(QLabel("產生的語法："))
        function_layout.addWidget(self.result_output)

        # 加入這段到合適 layout 中（中間區塊）
        self.syntax_result_label = QLabel("🧠 語法解析結果：")
        self.syntax_result_box = QTextEdit()
        self.syntax_result_box.setReadOnly(True)

        function_layout.addWidget(self.syntax_result_label)
        function_layout.addWidget(self.syntax_result_box)

        # 分頁加入
        self.function_tab_index = self.tab_widget.addTab(function_tab, "函數指令")
        main_layout.addWidget(self.tab_widget)

  # 預先初始化一次

        





        # ===== 右側：模擬結果 + 裝備原始屬性 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)

        self.equip_text_label = QLabel("裝備屬性原始內容")
        right_layout.addWidget(self.equip_text_label)
        right_layout.addWidget(self.equip_text)
        right_layout.addWidget(self.sim_effect_label)
        #right_layout.addWidget(self.sim_effect_text)
        # === 效果解析分頁（兩個頁籤） ===
        self.sim_tabs = QTabWidget()
        right_layout.addWidget(self.sim_tabs)

        # 分頁1：單件裝備效果
        self.sim_effect_text = QTextEdit()
        self.sim_effect_text.setReadOnly(True)
        self.sim_tabs.addTab(self.sim_effect_text, "目前裝備效果")

        # 分頁2：總合套裝效果
        self.combo_effect_text = QTextEdit()
        self.combo_effect_text.setReadOnly(True)
        self.sim_tabs.addTab(self.combo_effect_text, "整體套裝效果")
        
        
        # 建立 總效果分頁 的容器
        total_tab_layout = QVBoxLayout()
        total_filter_input_sort_mode_combo = QHBoxLayout()

        # 🔍 篩選輸入欄
        self.total_filter_input = QLineEdit()
        self.total_filter_input.setPlaceholderText("🔍 篩選總效果（例如：詠唱）")
        self.total_filter_input.textChanged.connect(self.update_total_effect_display)        
        total_filter_input_sort_mode_combo.addWidget(self.total_filter_input)
        
        # 排序方式下拉選單
        self.sort_mode_combo = QComboBox()
        self.sort_mode_combo.addItems([
            "來源順序",          
            "依名稱",
            "增傷詞條",
            "ROCalculator輸入"
        ])
        self.sort_mode_combo.setCurrentText("增傷詞條")  # ✅ 預設選這個
        self.sort_mode_combo.currentIndexChanged.connect(self.trigger_total_effect_update)
        total_filter_input_sort_mode_combo.addWidget(self.sort_mode_combo)
        total_tab_layout.addLayout(total_filter_input_sort_mode_combo)
        
        # 📄 整體總效果文字框
        self.total_effect_text = QTextEdit()
        self.total_effect_text.setReadOnly(True)        
        total_tab_layout.addWidget(self.total_effect_text)

        # 將 layout 放進 QWidget，再加進分頁
        total_tab_widget = QWidget()
        total_tab_widget.setLayout(total_tab_layout)
        self.sim_tabs.addTab(total_tab_widget, "整體總效果")




        # 模擬效果隱藏選項
        self.hide_unrecognized_checkbox = QCheckBox("隱藏辨識內容")
        self.hide_unrecognized_checkbox.setChecked(True)  # 預設勾選
        self.hide_unrecognized_checkbox.stateChanged.connect(self.display_item_info)
        self.hide_unrecognized_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        #不控制裝備屬性原始內容顯示就註解掉下面那行
        self.hide_unrecognized_checkbox.stateChanged.connect(self.toggle_equip_text_visibility)
        right_layout.addWidget(self.hide_unrecognized_checkbox)
        
        # 效果解析下方
        self.hide_physical_checkbox = QCheckBox("隱藏物理")
        self.hide_magical_checkbox = QCheckBox("隱藏魔法")
        self.hide_physical_checkbox.stateChanged.connect(self.display_item_info)
        self.hide_magical_checkbox.stateChanged.connect(self.display_item_info)
        self.hide_physical_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        self.hide_magical_checkbox.stateChanged.connect(self.trigger_total_effect_update)
        # ✅ 套裝來源顯示勾選框
        self.show_combo_source_checkbox = QCheckBox("顯示來源")
        self.show_combo_source_checkbox.setChecked(True)  # 預設勾選
        self.show_combo_source_checkbox.stateChanged.connect(self.display_all_effects)
        self.show_combo_source_checkbox.stateChanged.connect(self.trigger_total_effect_update)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.hide_unrecognized_checkbox)
        checkbox_layout.addWidget(self.show_combo_source_checkbox)
        checkbox_layout.addWidget(self.hide_physical_checkbox)
        checkbox_layout.addWidget(self.hide_magical_checkbox)
        
        right_layout.addLayout(checkbox_layout)

        # 建立新分頁：傷害計算
        self.custom_calc_tab = QWidget()
        layout = QVBoxLayout(self.custom_calc_tab)

        # 多行文字框
        #self.custom_calc_box = QTextEdit()
        #layout.addWidget(self.custom_calc_box)
        
        # 多行文字框
        self.custom_calc_box = QTextEdit()
        monospace_font = QFont("MingLiU")  # 或你喜歡的等寬字體，例如 "Courier New"
        monospace_font.setStyleHint(QFont.Monospace)
        #monospace_font.setPointSize(11)  # 依你的 UI 調整字體大小
        self.custom_calc_box.setFont(monospace_font)

        layout.addWidget(self.custom_calc_box)

        
        
        
        def filter_skills():
            text = self.skill_filter_input.text().strip().lower()
            self.skill_box.blockSignals(True)  # 暫時停止訊號，避免重複觸發

            self.skill_box.clear()

            for key, display_name in skill_map.items():
                skill_data = skill_map_all.get(key)
                slv = skill_data.get("Slv") if skill_data else None

                # 無搜尋文字時，只顯示有 Slv 的技能
                if text == "":
                    if pd.notna(slv) and str(slv).strip() != "":
                        self.skill_box.addItem(display_name, key)
                else:
                    # 有搜尋時顯示所有技能（包含沒有 Slv）
                    if text in display_name.lower():
                        self.skill_box.addItem(display_name, key)

            self.skill_box.blockSignals(False)

            # 若有項目，自動選第一個並更新顯示
            if self.skill_box.count() > 0:
                self.skill_box.setCurrentIndex(0)
                update_skill_formula_display()
            else:
                # 清空顯示
                self.skill_formula_result_input.setText("0%")
                self.skill_LV_input.setText("0")
                self.skill_hits_input.setText("")



        
        skill_select_layout_top = QHBoxLayout()
        skill_select_layout_bottom = QHBoxLayout()

        # 技能過濾輸入欄
        self.skill_filter_input = QLineEdit()
        self.skill_filter_input.setPlaceholderText("技能過濾")
        self.skill_filter_input.setFixedWidth(80)
        skill_select_layout_top.addWidget(self.skill_filter_input)
        self.skill_filter_input.textChanged.connect(filter_skills)
        


        def update_skill_formula_display():
            current_data = self.skill_box.currentData()
            skill_data = skill_map_all.get(current_data)

            # 沒有資料時清空
            if not skill_data or not skill_data.get("Calculation"):
                self.skill_formula_result_input.setText("0%")
                self.skill_LV_input.setText("0")
                self.skill_hits_input.setText("")
                return

            # 技能公式
            formula = skill_data.get("Calculation", "")
            self.skill_formula_input.setText(str(formula))

            # 技能等級
            skill_lv_raw = skill_data.get("Slv", "")
            try:
                lv = float(skill_lv_raw)
                self.skill_LV_input.setText(f"{lv:.0f}")
            except:
                lv = 1
                self.skill_LV_input.setText("")

            # 打擊次數（支援公式 + 負數）
            skill_hits = skill_data.get("hits", "")
            try:
                expr = sympify(str(skill_hits))
                hits_result = int(expr.evalf(subs={"Sklv": lv}))
                self.skill_hits_input.setText(f"{hits_result}")
            except:
                self.skill_hits_input.setText(str(skill_hits))





            # 設定屬性下拉
            element_key = skill_data.get("element", "")
            index = self.attack_element_box.findData(element_key)
            if index != -1:
                self.attack_element_box.setCurrentIndex(index)

            # 呼叫更新計算
            self.replace_custom_calc_content()

        # 技能下拉選單
        self.skill_box = QComboBox()
        self.skill_box.setFixedWidth(160)

        for key in skill_map:
            skill_data = skill_map_all.get(key)
            slv = skill_data.get("Slv") if skill_data else None

            # 過濾 Slv 為空、空字串、None、NaN
            if pd.notna(slv) and str(slv).strip() != "":
                self.skill_box.addItem(skill_map[key], key)

        # 綁定更新函式
        self.skill_box.currentIndexChanged.connect(update_skill_formula_display)
        skill_select_layout_top.addWidget(self.skill_box)

        # 技能等級
        self.skill_LV_input = QLineEdit()
        self.skill_LV_input.setPlaceholderText("技能等級")
        #self.skill_LV_input.setReadOnly(True)
        self.skill_LV_input.setFixedWidth(40)
        skill_select_layout_top.addWidget(self.skill_LV_input)

        # 攻擊屬性
        self.attack_element_box = QComboBox()
        for key in range(0, 10):
            self.attack_element_box.addItem(element_map[key], key)
        self.attack_element_box.setFixedWidth(80)
        skill_select_layout_top.addWidget(self.attack_element_box)
        
        # 公式結果欄
        
        self.skill_hits_input = QLineEdit()
        self.skill_hits_input.setPlaceholderText("次數")
        self.skill_hits_input.setText("1")
        self.skill_hits_input.setReadOnly(True)
        self.skill_hits_input.setFixedWidth(40)
        skill_select_layout_top.addWidget(self.skill_hits_input)


        # 技能公式欄
        self.skill_formula_input = QLineEdit()
        self.skill_formula_input.setPlaceholderText("技能公式")
        self.skill_formula_input.setFixedWidth(450)
        skill_select_layout_bottom.addWidget(self.skill_formula_input)

        # 公式結果欄
        self.skill_formula_result_input = QLineEdit()
        self.skill_formula_result_input.setPlaceholderText("公式結果")
        self.skill_formula_result_input.setReadOnly(True)
        self.skill_formula_result_input.setFixedWidth(100)
        skill_select_layout_bottom.addWidget(self.skill_formula_result_input)
        

        
        layout.insertLayout(0, skill_select_layout_top)
        layout.insertLayout(1, skill_select_layout_bottom)
        
        # 建立水平區塊
        button_row = QHBoxLayout()

        self.save_compare_button = QPushButton("儲存比對基準")
        self.save_compare_button.clicked.connect(self.save_compare_base)
        button_row.addWidget(self.save_compare_button)

        # 中間新增勾選框
        self.auto_compare_checkbox = QCheckBox("持續比對")
        button_row.addWidget(self.auto_compare_checkbox)
        
        self.compare_button = QPushButton("手動執行比對")
        self.compare_button.clicked.connect(self.compare_with_base)
        button_row.addWidget(self.compare_button)
        
        self.reskill_map_button = QPushButton("重新載入技能表")
        self.reskill_map_button.clicked.connect(load_skill_map)
        self.reskill_map_button.clicked.connect(filter_skills)
        
        button_row.addWidget(self.reskill_map_button)



        layout.addLayout(button_row)

        # 把這整排按鈕加進主 layout（通常是 QVBoxLayout）
        layout.addLayout(button_row)


        # 插入分隔線（放在第 2 行之後）
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(2, separator)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(4, separator)

        # === 特殊效果勾選區塊 ===

        # 使用 QGridLayout 來自動排版，每行最多放 4 個
        special_checkbox_layout = QGridLayout()
        
        # 特殊效果增傷處理區
        self.special_checkboxes = {
            "wanzih_checkbox": QCheckBox("萬紫千紅(巔峰4)"),
            "magic_poison_checkbox": QCheckBox("魔力中毒"),
            "attribute_seal_checkbox": QCheckBox("屬性紋章(水地火風)"),
            "sneak_attack_checkbox": QCheckBox("潛擊"),
            # 可在這裡繼續新增更多項目
        }


        # 加入 layout（最多每行 4 個）
        max_per_row = 4
        for index, (key, checkbox) in enumerate(self.special_checkboxes.items()):
            row = index // max_per_row
            col = index % max_per_row
            special_checkbox_layout.addWidget(checkbox, row, col)

        layout.addLayout(special_checkbox_layout)
        
        # ✅ 在這裡綁定觸發
        for checkbox in self.special_checkboxes.values():
            checkbox.stateChanged.connect(self.replace_custom_calc_content)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.insertWidget(6, separator)


        # === 建立目標設定區塊 ===
        target_layout = QHBoxLayout()

        # 建立下拉選單函式
        def make_combobox(label_text, options, visible_keys=None):
            sub_layout = QVBoxLayout()
            label = QLabel(label_text)
            box = QComboBox()
            
            if visible_keys is None:
                visible_keys = options.keys()
            
            for key in visible_keys:
                box.addItem(options[key], key)
            
            sub_layout.addWidget(label)
            sub_layout.addWidget(box)
            return sub_layout, box

        # 體型
        size_layout, self.size_box = make_combobox("體型", size_map)
        target_layout.addLayout(size_layout)

        # 屬性
        # 只顯示 element_map 前 10 個 key（0~9）
        visible_element_keys = [k for k in element_map if k <= 9]
        element_layout, self.element_box = make_combobox("屬性", element_map, visible_element_keys)
        target_layout.addLayout(element_layout)
        
        element_lv_input_layout = QVBoxLayout()
        element_lv_input_label = QLabel("等級")
        self.element_lv_input = QLineEdit()
        self.element_lv_input.setFixedWidth(30)
        self.element_lv_input.setPlaceholderText("1")
        validator = QIntValidator(1, 4, self)
        self.element_lv_input.setValidator(validator)
        element_lv_input_layout.addWidget(element_lv_input_label)
        element_lv_input_layout.addWidget(self.element_lv_input)
        target_layout.addLayout(element_lv_input_layout)
        
        #指定魔物增傷
        monsterDamage_layout = QVBoxLayout()
        self.monsterDamage_label = QLabel("魔物增傷")
        self.monsterDamage_input = QLineEdit()
        self.monsterDamage_input.setFixedWidth(60)
        self.monsterDamage_input.setPlaceholderText("0")
        monsterDamage_layout.addWidget(self.monsterDamage_label)
        monsterDamage_layout.addWidget(self.monsterDamage_input)
        target_layout.addLayout(monsterDamage_layout)
        self.monsterDamage_label.setVisible(False)#UI暫時隱藏
        self.monsterDamage_input.setVisible(False)

        # 同樣方式套用在 race_map（假設你也要限制）
        visible_race_keys = [k for k in race_map if k <= 9]
        race_layout, self.race_box = make_combobox("種族", race_map, visible_race_keys)
        target_layout.addLayout(race_layout)


        # 階級
        visible_class_keys = [k for k in class_map if k <= 1]  # 依你需求調整
        class_layout, self.class_box = make_combobox("階級", class_map, visible_class_keys)
        target_layout.addLayout(class_layout)

        # MDEF / MRES 輸入欄
        def_layout = QVBoxLayout()
        self.def_label = QLabel("前DEF")
        self.def_input = QLineEdit()
        self.def_input.setFixedWidth(60)
        self.def_input.setPlaceholderText("0")
        self.mdef_label = QLabel("前MDEF")
        self.mdef_input = QLineEdit()
        self.mdef_input.setFixedWidth(60)
        self.mdef_input.setPlaceholderText("0")
        def_layout.addWidget(self.def_label)
        def_layout.addWidget(self.def_input)        
        def_layout.addWidget(self.mdef_label)
        def_layout.addWidget(self.mdef_input)
        target_layout.addLayout(def_layout)

        
        defc_layout = QVBoxLayout()
        self.defc_label = QLabel("後DEF")
        self.defc_input = QLineEdit()
        self.defc_input.setFixedWidth(60)
        self.defc_input.setPlaceholderText("0")
        self.mdefc_label = QLabel("後MDEF")
        self.mdefc_input = QLineEdit()
        self.mdefc_input.setFixedWidth(60)
        self.mdefc_input.setPlaceholderText("0")
        defc_layout.addWidget(self.defc_label)
        defc_layout.addWidget(self.defc_input)
        defc_layout.addWidget(self.mdefc_label)
        defc_layout.addWidget(self.mdefc_input)
        target_layout.addLayout(defc_layout)


        res_layout = QVBoxLayout()
        self.res_label = QLabel("RES")
        self.res_input = QLineEdit()
        self.res_input.setFixedWidth(60)
        self.res_input.setPlaceholderText("0")
        self.mres_label = QLabel("MRES")
        self.mres_input = QLineEdit()
        self.mres_input.setFixedWidth(60)
        self.mres_input.setPlaceholderText("0")
        res_layout.addWidget(self.res_label)
        res_layout.addWidget(self.res_input)
        res_layout.addWidget(self.mres_label)
        res_layout.addWidget(self.mres_input)
        target_layout.addLayout(res_layout)
        
        self.def_label.setVisible(False)
        self.def_input.setVisible(False)
        self.defc_label.setVisible(False)
        self.defc_input.setVisible(False)
        self.res_label.setVisible(False)
        self.res_input.setVisible(False)
        
        # 把整排放到主要 layout
        
        layout.addLayout(target_layout)
        
        # ComboBox 的綁定 修改觸發計算
        self.size_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.element_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.race_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.class_box.currentIndexChanged.connect(self.replace_custom_calc_content)
        self.attack_element_box.currentIndexChanged.connect(self.replace_custom_calc_content)

        # LineEdit 的綁定（使用 editingFinished 避免每次打字都觸發）
        self.monsterDamage_input.editingFinished.connect(self.replace_custom_calc_content)
        self.def_input.editingFinished.connect(self.replace_custom_calc_content)
        self.defc_input.editingFinished.connect(self.replace_custom_calc_content)
        self.res_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mdef_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mdefc_input.editingFinished.connect(self.replace_custom_calc_content)
        self.mres_input.editingFinished.connect(self.replace_custom_calc_content)


        # 新增按鈕
        self.replace_calc_button = QPushButton("計算")
        self.replace_calc_button.clicked.connect(lambda: (setattr(self, "_last_calc_state", None), self.replace_custom_calc_content()))
        layout.addWidget(self.replace_calc_button)

        self.sim_tabs.addTab(self.custom_calc_tab, "傷害計算")







        # ===== 合併三欄 =====
        #main_layout.addWidget(left_scroll, 2)#已分頁取代
        #main_layout.addWidget(middle_scroll, 3)
        main_layout.addWidget(right_scroll, 3)
        self.setLayout(main_layout)


        # 初始化下拉選單
        self.update_combobox(initial=True)
        self.current_edit_part = None  # 用來追蹤目前編輯哪個欄位

        #根據 checkbox 狀態隱藏或顯示
        self.toggle_equip_text_visibility()


        #讀取.json存檔 250611更動工具列讀取
        #self.load_saved_inputs()
        



        #讀取完先計算一次        
        
        self.display_all_effects()
        



        # 初始顯示一次
        
        self.update_dex_int_half_note()
        self.result_output.textChanged.connect(self.on_result_output_changed)
        self.gen_button.clicked.connect(self.on_generate)
        self.function_selector.currentIndexChanged.connect(self.on_function_changed)
        self.on_function_changed()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        # 綁定輸入欄事件（動態更新）
        self.input_fields["DEX"].textChanged.connect(self.update_dex_int_half_note)
        self.input_fields["INT"].textChanged.connect(self.update_dex_int_half_note)
        #開啟選單欄 
        self.update_window_title()
        self.setup_menu()
        
    
    def setup_menu(self):
        menubar = QMenuBar(self)

        # === 檔案選單 ===
        file_menu = menubar.addMenu("檔案")

        open_action = QAction("開啟", self)
        open_action.triggered.connect(self.open_project_file)
        file_menu.addAction(open_action)        

        save_action = QAction("存檔", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存新檔", self)
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)

        ROC_save_as_action = QAction("另存到.ROC(ROCalculator)", self)
        ROC_save_as_action.triggered.connect(
            lambda checked=False: self.add_effects_from_variables("data\default.txt", equipid_mapping, status_mapping)
        )   

        file_menu.addAction(ROC_save_as_action)
        '''
        # === 設定選單 ===
        settings_menu = menubar.addMenu("設定")

        preferences_action = QAction("偏好設定()", self)
        preferences_action.triggered.connect#(self.open_preferences)
        settings_menu.addAction(preferences_action)


        # === 說明選單 ===
        help_menu = menubar.addMenu("說明")

        help_action = QAction("使用說明", self)
        help_action.triggered.connect#(self.show_help)
        help_menu.addAction(help_action)

        about_action = QAction("關於", self)
        about_action.triggered.connect#(self.show_about)
        help_menu.addAction(about_action)
        '''
        # === 加入選單到主 layout ===
        self.layout().setMenuBar(menubar)
        


    def add_effects_from_variables(self, template_path, equipid_mapping, status_mapping):  # 直接輸出 .ROC
        import json, copy, os, base64
        from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

        # === 擷取類別或全域變數 ===
        context = globals()

        # === 讀取模板 JSON ===
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        new_data = copy.deepcopy(template)

        # === 找到主手裝備的 effectlist ===
        equip_list = new_data.get("Equip", [])
        if not equip_list:
            QMessageBox.warning(self, "錯誤", "模板檔案中沒有 Equip 資料")
            return
        effect_list = equip_list[0].get("effectlist", [])

        # === 根據 equipid_mapping 新增效果到 Equip ===
        for var_name, effect_id in equipid_mapping.items():
            if var_name in context:
                value = context[var_name]
                new_effect = {
                    "EffectNumber": value,
                    "EffectType": {"id": effect_id},
                    "Enable": True
                }
                effect_list.append(new_effect)
                print(f"✅ 已新增效果：{effect_id} = {value}")
            else:
                print(f"⚠️ 找不到變數：{var_name}，略過。")

        # === 根據 status_mapping 更新 Status ===
        status_data = new_data.get("Status", {})
        if status_data:
            for var_name, status_key in status_mapping.items():
                if var_name in context:
                    new_value = context[var_name]
                    old_value = status_data.get(status_key, None)
                    status_data[status_key] = new_value
                    print(f"🔄 Status[{status_key}] 從 {old_value} → {new_value}")
                else:
                    print(f"⚠️ 找不到變數：{var_name}（對應 Status[{status_key}]），略過。")
        else:
            print("⚠️ 模板中沒有 Status 區塊。")

        # === 根據 weapon_mapping 更新 Weapon ===
        weapon_data = new_data.get("Weapon", {})
        if weapon_data:
            for var_name, weapon_key in weapon_mapping.items():
                if var_name in context:
                    new_value = context[var_name]

                    # weapon_key 可能是單層或雙層 key
                    if isinstance(weapon_key, tuple) and len(weapon_key) == 2:
                        first, second = weapon_key
                        if first in weapon_data and isinstance(weapon_data[first], dict):
                            old_value = weapon_data[first].get(second, None)
                            weapon_data[first][second] = new_value
                            print(f"🔄 Weapon[{first}][{second}] 從 {old_value} → {new_value}")
                        else:
                            print(f"⚠️ Weapon 中沒有 {first} 層級，略過。")
                    else:
                        old_value = weapon_data.get(weapon_key, None)
                        weapon_data[weapon_key] = new_value
                        print(f"🔄 Weapon[{weapon_key}] 從 {old_value} → {new_value}")
                else:
                    print(f"⚠️ 找不到變數：{var_name}（對應 Weapon[{weapon_key}]），略過。")
        else:
            print("⚠️ 模板中沒有 Weapon 區塊。")

        # === 從視窗標題推斷檔名 ===
        full_title = self.windowTitle().strip() or "RO物品查詢計算工具 - 未命名"
        if " - " in full_title:
            filename_part = full_title.split(" - ", 1)[1]
        else:
            filename_part = "未命名"

        for bad_char in '\\/:*?"<>|':
            filename_part = filename_part.replace(bad_char, "_")

        filename_part = os.path.splitext(filename_part)[0]
        suggested_filename = f"{filename_part}.roc"

        # === 顯示另存新檔 ===
        app = QApplication.instance() or QApplication([])
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存 ROC 檔",
            suggested_filename,
            "ROC 檔案 (*.roc)"
        )

        if not file_path:
            return

        # 確保副檔名正確
        if not file_path.lower().endswith(".roc"):
            file_path += ".roc"

        # === 直接轉成 base64 並寫出 ROC 檔 ===
        try:
            encoded = base64.b64encode(json.dumps(new_data, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(encoded)
            print(f"✅ 已新增效果並更新 Status，直接輸出 ROC 檔：{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"ROC 轉換或儲存失敗：{e}")
            print(f"❌ 轉換失敗：{e}")





        
        
    def save_as_file(self):
        # 預設開啟的資料夾
        default_dir = os.path.join(os.getcwd(),"裝備")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存新檔",
            default_dir,  # ✅ 預設路徑
            "JSON Files (*.json)"
        )

        if file_path:
            # 確保副檔名是 .json
            if not file_path.lower().endswith(".json"):
                file_path += ".json"

            self.save_to_file(file_path)
            
    def save_to_file(self, file_path):
        data = {}

        # 儲存 input_fields
        for key, field in self.input_fields.items():
            if isinstance(field, QComboBox):
                data[key] = field.currentText()
            else:
                data[key] = field.text()

        # 儲存裝備與卡片欄位
        for part, info in self.refine_inputs_ui.items():
            data[f"{part}_equip"] = info["equip"].text()
            for i, card_input in enumerate(info["cards"]):
                data[f"{part}_card{i+1}"] = card_input.text()
            if "note" in info:
                data[f"{part}_note"] = info["note"].toPlainText()

        # 技能與怪物資訊整合
        data["skill_name"] = self.skill_box.currentText()
        data["size"] = self.size_box.currentIndex()
        data["element"] = self.element_box.currentIndex()
        data["race"] = self.race_box.currentIndex()
        data["class"] = self.class_box.currentIndex()
        data["mdef"] = self.mdef_input.text()
        data["mdefc"] = self.mdefc_input.text()
        data["mres"] = self.mres_input.text()
        data["def"] = self.def_input.text()
        data["defc"] = self.defc_input.text()
        data["res"] = self.res_input.text()
        data["element_lv"] = self.element_lv_input.text()

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.current_file = file_path
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"無法儲存檔案：\n{e}")


    def save_file(self):
        if not self.current_file:
            self.save_as_file()  # 如果還沒指定檔案，就當成另存新檔
        else:
            self.save_to_file(self.current_file)





    def open_project_file(self):
        # 設定預設資料夾
        default_dir = os.path.join(os.getcwd(),"裝備")
    
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇專案檔",
            default_dir,  # ✅ 預設資料夾
            "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            self.skill_filter_input.clear()
            self.load_saved_inputs(file_path)
            self.current_file = file_path
            self.update_window_title()
            self.display_all_effects()
            self.update_dex_int_half_note()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入失敗：\n{str(e)}")



    def clear_current_edit(self):
        self.current_edit_part = None
        self.current_edit_label.setText("目前部位：")
        self.unsync_button.setVisible(False)
        self.apply_equip_button.setVisible(False)
        self.unsync_button2.setVisible(False)
        self.apply_to_note_button.setVisible(False)
        self.clear_field_button2.setVisible(False)
        self.clear_field_button.setVisible(False)

        for part_name, widgets in self.refine_inputs_ui.items():
            widgets["equip"].setEnabled(True)
            widgets["refine"].setEnabled(True)
            widgets["grade"].setEnabled(True)
            for card_input in widgets["cards"]:
                card_input.setEnabled(True)
            # ✅ 移除所有欄位的背景色
            widgets["equip"].setStyleSheet("")
            for card_input in widgets["cards"]:
                card_input.setStyleSheet("")
            widgets["note"].setStyleSheet("")
            widgets["note_ui"].setStyleSheet("")
            
        self.display_item_info()
        self.display_all_effects()
        self.global_refine_input.setVisible(True)
        self.global_grade_combo.setVisible(True)





    def set_edit_lock(self, part_name, field_name):


        self.display_item_info()
        self.global_refine_input.setVisible(False)
        self.global_grade_combo.setVisible(False)


    def update_combobox(self, initial=False):
        keyword = self.search_input.text().strip()
        self.result_box.clear()

        # 只保留有裝備效果資料的項目，並根據關鍵字過濾
        self.filtered_items = {
            k: v for k, v in self.parsed_items.items()
            if k in self.equipment_data and (
                keyword in str(k) or
                keyword in v['name'] or
                any(keyword in line for line in v['description'])
            )
        }

        for item_id in sorted(self.filtered_items):
            item = self.filtered_items[item_id]
            self.result_box.addItem(f"{item_id} - {item['name']}", item_id)

        if self.result_box.count() > 0:
            self.result_box.setCurrentIndex(0)
            self.display_item_info()

            


   
    def display_item_info(self, refine_override=None, grade_override=None):

        index = self.result_box.currentIndex()
        if index == -1:
            return
        item_id = self.result_box.currentData()
        item = self.filtered_items.get(item_id)
        if not item:
            return
        self.name_field.setText(item['name'])
        self.kr_name_field.setText(item['kr_name'])
        self.slot_field.setText(str(item['slot']))

        html = convert_description_to_html(item['description'])
        self.desc_text.setHtml(html)
        # 顯示裝備原始資料區塊（若有）
        if item_id in self.equipment_data:
            block_text = self.equipment_data[item_id]
            full_text = f"[{item_id}] = {{\n{block_text}\n}}"
            self.equip_text.setPlainText(full_text)
        else:
            self.equip_text.setPlainText("（此物品無對應裝備屬性資料）")
        # 模擬效果解析
        if item_id in self.equipment_data:
            # 偵測是否需要精煉欄位
            #self.refine_input.setVisible("GetRefineLevel(" in block_text)

            # 整理 get(...) 對應值
            get_values = {}
            for label, gid in self.stat_fields.items():
                widget = self.input_fields[label]
                if isinstance(widget, QComboBox):
                    get_values[gid] = widget.currentData()
                else:
                    try:
                        get_values[gid] = int(widget.text())
                    except ValueError:
                        get_values[gid] = 0

            # 整理 GetRefineLevel(...) 對應值
            refine_inputs = {}
            for label, info in self.refine_parts.items():
                slot_id = info["slot"]
                # 如果你原本使用 slot_id 做什麼，照樣用

                text = self.input_fields[label].text()
                try:
                    refine_inputs[slot_id] = int(text)
                except ValueError:
                    refine_inputs[slot_id] = 0

            # 裝備階級 GetEquipGradeLevel
            grade = 0
            if hasattr(self, "current_edit_part") and self.current_edit_part:
                part_name = self.current_edit_part.split(" - ")[0]
                key = f"{part_name}_階級"
                if key in self.input_fields:
                    grade = self.input_fields[key].currentIndex()
            
            hide_physical = self.hide_physical_checkbox.isChecked()
            hide_magical = self.hide_magical_checkbox.isChecked()
            hide_unrecognized = self.hide_unrecognized_checkbox.isChecked()
            # 抓目前裝備部位的 slot ID
            current_slot = None
            if self.current_edit_part:
                part_name = self.current_edit_part.split(" - ")[0]
                current_slot = self.refine_parts.get(part_name, {}).get("slot")
                grade = self.input_fields.get(f"{part_name}_階級", self.global_grade_combo).currentIndex()
            else:
                # ⬅️ 若沒選部位就用全域
                current_slot = None
                try:
                    refine_inputs[99] = int(self.global_refine_input.text())  # slot=99 為假設值
                except:
                    refine_inputs[99] = 0
                grade = self.global_grade_combo.currentIndex()


            # 呼叫新模擬效果解析器
            effects = parse_lua_effects_with_variables(
                block_text,
                refine_inputs,
                get_values,
                grade,
                unit_map,
                size_map,
                effect_map,
                hide_unrecognized,
                current_location_slot=current_slot or 99
            )


            hide_keywords = []
            if hide_physical:
                hide_keywords.append("物理")
            if hide_magical:
                hide_keywords.append("魔法")
                
            filtered_effects = self.filter_effects(effects)
            effect_dict = {}
            for line in filtered_effects:
                parsed = self.try_extract_effect(line)
                if parsed:
                    key, value, unit = parsed
                    key = self.normalize_effect_key(key)
                    #source_label = part_name  # or 卡片名稱 or 套裝來源

                    # 建立效果來源清單
                    #effect_dict.setdefault((key, unit), []).append((value, source_label))


                else:
                    continue  # 無法解析就略過，不佔用空間



            combined = []
            show_source = self.show_combo_source_checkbox.isChecked()
            for (key, unit), entries in sorted(effect_dict.items(), key=lambda x: x[0][0]):
                total = sum(val for val, _ in entries)
                if unit == "秒":
                    total = round(total, 1)
                    value_str = f"{total:+.1f}{unit}"
                else:
                    value_str = f"{total:+g}{unit}"

                if show_source:
                    for val, source in entries:
                        val_str = f"{val:+.1f}{unit}" if unit == "秒" else f"{val:+d}{unit}"
                        combined.append(f"{key} {val_str}  ← 〔{source}〕")
                    combined.append(f"🧮{key} {value_str}  ← 〔總和〕🧮")
                else:
                    combined.append(f"{key} {value_str}")
    




            self.sim_effect_text.setPlainText("\n".join(combined))
            # 顯示結果
            self.sim_effect_text.setPlainText("\n".join(filtered_effects))
            
            self.display_all_effects()
            
            
        else:
            self.sim_effect_text.setPlainText("（無可解析效果）")
            

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loading = LoadingDialog()
    loading.show()    

    window = ItemSearchApp()
    worker = InitWorker(app_instance=window)

    worker.log_signal.connect(loading.append_text)
    worker.progress_signal.connect(loading.update_progress)

    def on_done(data):
        loading.append_text("初始化完成，正在更新介面...")

        # ✅ 主執行緒更新 UI
        window.parsed_items = data or {}
        window.update_combobox()

        window.resize(1500, 800)
        window.show()

        QTimer.singleShot(1000, loading.close)

    worker.done_signal.connect(on_done)
    worker.start()

    sys.exit(app.exec())
