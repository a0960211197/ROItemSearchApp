import sys
import pandas as pd
import yaml
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QComboBox, QLabel, QScrollArea, QGridLayout,
    QPushButton, QHBoxLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt


# =========================================================
# 設定路徑
# =========================================================
SKILL_CSV_PATH = r"data\skillneme.csv"
SKILL_TREE_YML_PATH = r"data\skill_tree.yml"
import re

TREEVIEW_LUB_PATH = r"data\skilltreeview.lub"

# job_name -> { skill_code -> index }
treeview_positions = {}

def _jt_to_id_jobneme(jt_name: str) -> str:
    """
    將 'DRAGON_KNIGHT' 轉成 'Dragon_Knight'
    和你 job_dict 裡的 id_jobneme 對齊。
    """
    return "_".join(p.capitalize() for p in jt_name.lower().split("_"))

def load_skill_treeview(filepath: str = TREEVIEW_LUB_PATH):
    global treeview_positions
    treeview_positions = {}

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lua = f.read()

    pattern = re.compile(
        r"\[JOBID\.JT_([A-Z0-9_]+)\]\s*=\s*\{(.*?)\}",
        re.S
    )
    matches = pattern.findall(lua)

    for jt_name, body in matches:
        job_key = _jt_to_id_jobneme(jt_name)  # 例如 DRAGON_KNIGHT -> Dragon_Knight
        pairs = re.findall(r"\[(\d+)\]\s*=\s*SKID\.([A-Z0-9_]+)", body)
        if not pairs:
            continue
        pos_map = {code: int(idx) for idx, code in pairs}
        treeview_positions[job_key] = pos_map

    print(f"skilltreeview.lub 解析完成，職業數：{len(treeview_positions)}")


def get_combined_pos_map(job_key: str) -> dict:
    """
    取得某個 4 轉職業的完整技能排序：
    - 先塞 1/2/3 轉 (id_jobneme_OL)
    - 再塞 4 轉本身 (id_jobneme)
    之後 SkillTreeGrid 只會拿有 skills 的 code 來排，所以多塞不會爆。
    """
    pos_map: dict[str, int] = {}

    # 先找到這個 job_key 在 job_dict 的 entry
    job_entry = None
    for _, j in job_dict.items():
        if j.get("id_jobneme") == job_key:
            job_entry = j
            break

    # 先處理舊轉職 (1/2/3 轉)
    if job_entry:
        ol = job_entry.get("id_jobneme_OL")
        if ol:
            for name in ol.split("/"):
                name = name.strip()
                if not name:
                    continue
                pm = treeview_positions.get(name)
                if not pm:
                    continue
                # 不覆蓋已存在的 index（避免互相踢掉）
                for code, idx in pm.items():
                    pos_map.setdefault(code, idx)

    # 再處理 4 轉本身，讓 4 轉的 index 優先（覆蓋舊的）
    base_pm = treeview_positions.get(job_key, {})
    for code, idx in base_pm.items():
        pos_map[code] = idx

    return pos_map

#6大12分支職業點數 "point":"49/49/20/49/54"

# =========================================================
# job_dict (你給的這個)
# =========================================================

job_dict = {
    4252: {"id": "RK","id_jobneme": "Dragon_Knight","id_jobneme_OL": "Swordman/Knight/Knight_H/Rune_Knight","selectskill": "RK/DK", "name": "盧恩龍爵", "TJobMaxPoint": [6,8,7,8,8,6,10,6,3,5,6,8]},
    4253: {"id": "ME","id_jobneme": "Meister","id_jobneme_OL": "Merchant/Blacksmith/Blacksmith_H/Mechanic","selectskill": "NC/MT", "name": "機甲神匠", "TJobMaxPoint": [10,6,10,6,5,6,9,10,5,0,7,7]},
    4254: {"id": "GX","id_jobneme": "Shadow_Cross","id_jobneme_OL": "Thief/Assassin/Assassin_H/Guillotine_Cross","selectskill": "GC/ASC/SHC", "name": "十字影武", "TJobMaxPoint": [8,11,6,5,9,4,12,8,4,0,7,7]},
    4255: {"id": "WL","id_jobneme": "Arch_Mage","id_jobneme_OL": "Magician/Wizard/Wizard_H/Warlock","selectskill": "WL/AG", "name": "禁咒魔導士", "TJobMaxPoint": [1,7,8,15,8,4,0,8,7,13,9,1]},
    4256: {"id": "AB","id_jobneme": "Cardinal","id_jobneme_OL": "Acolyte/Priest/Priest_H/Archbishop","selectskill": "AB/CD", "name": "樞機主教", "TJobMaxPoint": [6,7,7,12,7,4,8,5,5,9,4,7]},
    4257: {"id": "RA","id_jobneme": "Wind_Hawk","id_jobneme_OL": "Archer/Hunter/Hunter_H/Ranger","selectskill": "SN/RA/WH", "name": "風鷹狩獵者", "TJobMaxPoint": [2,12,8,9,8,4,9,5,5,4,11,4]},
    4258: {"id": "RG","id_jobneme": "Imperial_Guard","id_jobneme_OL": "Swordman/Crusader/Crusader_H/Royal_Guard","selectskill": "LG/PA/IG", "name": "帝國聖衛軍", "TJobMaxPoint": [9,3,9,10,9,3,7,11,6,7,4,3]},
    4259: {"id": "GE","id_jobneme": "Biolo","id_jobneme_OL": "Merchant/Alchemist/Alchemist_H/Genetic","selectskill": "GN/CR/BO", "name": "生命締造者", "TJobMaxPoint": [5,6,8,12,8,4,7,4,4,4,7,12]},
    4260: {"id": "SC","id_jobneme": "Abyss_Chaser","id_jobneme_OL": "Thief/Rogue/Rogue_H/Shadow_Chaser","selectskill": "SC/ABC", "name": "深淵追跡者", "TJobMaxPoint": [8,9,8,6,6,6,8,8,4,7,5,6]},
    4261: {"id": "SO","id_jobneme": "Elemental_Master","id_jobneme_OL": "Magician/Sage/Sage_H/Sorcerer","selectskill": "SO/EM", "name": "元素支配者", "TJobMaxPoint": [4,4,8,13,9,5,3,8,7,12,5,3]},
    4262: {"id": "SU","id_jobneme": "Inquisitor","id_jobneme_OL": "Acolyte/Monk/Monk_H/Sura","selectskill": "MO/SR/IQ", "name": "聖裁者", "TJobMaxPoint": [10,10,6,8,8,1,11,8,5,3,5,6]},
    4263: {"id": "MI","id_jobneme": "Troubadour","id_jobneme_OL": "Archer/Bard/Bard_H/Minstrel","selectskill": "CG/WM/TR", "name": "天籟頌者", "TJobMaxPoint": [7,7,7,9,10,3,6,7,4,6,11,4]},
    4264: {"id": "WA","id_jobneme": "Trouvere","id_jobneme_OL": "Archer/Dancer/Dancer_H/Wanderer","selectskill": "CG/WM/TR", "name": "樂之舞靈", "TJobMaxPoint": [7,9,6,10,8,3,6,7,4,6,11,4]},
    4308: {"id": "SUM","id_jobneme": "Spirit_Handler","id_jobneme_OL": "Do_Summoner","selectskill": "SU/SH", "name": "魂靈師", "TJobMaxPoint": [5,7,5,9,12,5,8,6,5,8,7,4]},
    4307: {"id": "SN","id_jobneme": "Hyper_Novice","id_jobneme_OL": "Supernovice/Supernovice2","selectskill": "HN", "name": "終極初學者", "TJobMaxPoint": [10,5,6,10,5,6,9,5,4,9,8,3]},
    4306: {"id": "RE","id_jobneme": "Night_Watch","id_jobneme_OL": "Gunslinger/Rebellion","selectskill": "RL/NW", "name": "夜行者", "TJobMaxPoint": [3,8,6,8,11,7,11,6,5,0,10,5]},
    4304: {"id": "OB","id_jobneme": "Shinkiro","id_jobneme_OL": "Ninja/Kagerou","selectskill": "NJ/KO/SS", "name": "流浪忍者", "TJobMaxPoint": [10,12,6,4,9,3,10,10,4,0,6,8]},
    4305: {"id": "KO","id_jobneme": "Shiranui","id_jobneme_OL": "Ninja/Oboro","selectskill": "NJ/KO/SS", "name": "疾風忍者", "TJobMaxPoint": [4,8,5,10,10,3,4,8,10,3,6,7]},
    4303: {"id": "SL","id_jobneme": "Soul_Ascetic","id_jobneme_OL": "Taekwon/Linker/Soul_Reaper","selectskill": "SP/SOA", "name": "契靈士", "TJobMaxPoint": [3,7,7,11,13,2,0,8,7,16,7,3]},
    4302: {"id": "SE","id_jobneme": "Sky_Emperor","id_jobneme_OL": "Taekwon/Star/Star_Emperor","selectskill": "TK/SJ/SKE", "name": "天帝", "TJobMaxPoint": [12,10,6,3,9,3,12,10,2,0,6,7]},
}

# =========================================================
# skillneme.csv 對照：Code -> ID / 中文
# =========================================================
skill_id_to_name   = {}
skill_code_to_id   = {}
skill_code_to_name = {}

def load_skill_map(filepath=SKILL_CSV_PATH):
    global skill_id_to_name, skill_code_to_id, skill_code_to_name

    df = pd.read_csv(filepath, header=0)
    # 假設欄位：ID, Code, Name
    id_col   = "ID"
    code_col = "Code"
    name_col = "Name"

    skill_id_to_name   = dict(zip(df[id_col], df[name_col]))
    skill_code_to_id   = dict(zip(df[code_col], df[id_col]))
    skill_code_to_name = dict(zip(df[code_col], df[name_col]))

    print("讀入 skillneme.csv，欄位：", list(df.columns))


# =========================================================
# skill_tree.yml：Body: [ { Job, Inherit, Tree: [...] }, ... ]
# =========================================================
job_skill_tree_raw = {}

def load_skill_tree(filepath=SKILL_TREE_YML_PATH):
    global job_skill_tree_raw

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    body = data.get("Body", data)
    job_skill_tree_raw = {}
    for entry in body:
        job_name = entry.get("Job")
        if not job_name:
            continue
        inherit = entry.get("Inherit") or {}
        tree    = entry.get("Tree") or []
        job_skill_tree_raw[job_name] = {
            "inherit": inherit,
            "tree": tree,
        }
    print("讀入 skill_tree.yml，職業數：", len(job_skill_tree_raw))

def get_job_chain(job_key: str) -> list[str]:
    """
    給 4 轉的 job_key（例如 'Imperial_Guard'），
    回傳這條職業線的職業列表，例如：
    ['Swordman', 'Crusader', 'Royal_Guard', 'Imperial_Guard']
    """
    chain = []

    # 找到對應的 job_dict entry
    job_entry = None
    for _, j in job_dict.items():
        if j.get("id_jobneme") == job_key:
            job_entry = j
            break

    if job_entry:
        ol = job_entry.get("id_jobneme_OL", "")
        if ol:
            for name in ol.split("/"):
                name = name.strip()
                if name:
                    chain.append(name)

    # 最後把自己 4 轉也放進去
    chain.append(job_key)
    return chain


def build_job_skill_map(job_name, visited=None):
    """處理 Inherit + Exclude，輸出 {skill_code: skill_info}"""
    if visited is None:
        visited = set()
    if job_name in visited:
        return {}
    visited.add(job_name)

    if job_name not in job_skill_tree_raw:
        return {}

    job_data = job_skill_tree_raw[job_name]
    result = {}

    # 先繼承
    inherit = job_data.get("inherit") or {}
    for parent_job, use_it in inherit.items():
        if not use_it:
            continue
        parent_map = build_job_skill_map(parent_job, visited)
        for code, info in parent_map.items():
            if info.get("Exclude"):
                continue
            if code not in result:
                result[code] = info.copy()

    # 再加上自己的
    for s in job_data.get("tree", []):
        code = s.get("Name")
        if not code:
            continue
        result[code] = s.copy()

    return result


# =========================================================
# 計算技能「層級」（深度），用來決定放哪一欄
# =========================================================
def compute_skill_depths(skill_map_job: dict) -> dict:
    """
    沒有 Requires 的深度 = 0
    其他 = max(前置的深度) + 1
    """
    depths = {}

    def dfs(code, stack=None):
        if code in depths:
            return depths[code]
        if stack is None:
            stack = set()
        if code in stack:
            # 防止循環；爆掉就給 0
            return 0
        stack.add(code)

        info = skill_map_job.get(code, {})
        requires = info.get("Requires", []) or []
        if not requires:
            d = 0
        else:
            parent_depths = []
            for r in requires:
                parent_code = r.get("Name")
                if parent_code and parent_code in skill_map_job:
                    parent_depths.append(dfs(parent_code, stack))
            d = (max(parent_depths) + 1) if parent_depths else 0

        depths[code] = d
        stack.remove(code)
        return d

    for c in skill_map_job.keys():
        dfs(c)

    return depths


# =========================================================
# SkillNodeWidget：單一技能的小方塊
# =========================================================
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class SkillNodeWidget(QFrame):
    def __init__(self, code, get_level, max_level, inc_cb, dec_cb, parent=None):
        super().__init__(parent)
        self.code = code
        self.get_level = get_level
        self.inc_cb = inc_cb      # 加點 callback (父視窗的 increase_skill)
        self.dec_cb = dec_cb      # 減點 callback (父視窗的 decrease_skill)
        self.max_level = max_level

        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self.setCursor(Qt.PointingHandCursor)  # 滑鼠變小手

        self.setStyleSheet(
            "QFrame { background:#222; border-radius:4px; } "
            "QLabel { color:white; font-size:11px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 技能中文名稱
        cn_name = skill_code_to_name.get(code, code)
        self.lbl_name = QLabel(cn_name)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name)

        # 等級顯示
        self.lbl_level = QLabel()
        self.lbl_level.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_level)

        self.update_display()

    def update_display(self):
        lv = self.get_level(self.code)
        self.lbl_level.setText(f"Lv {lv}/{self.max_level}")
        # 有點數時背景亮一點
        if lv > 0:
            self.setStyleSheet(
                "QFrame { background:#444; border-radius:4px; } "
                "QLabel { color:white; font-size:11px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background:#222; border-radius:4px; } "
                "QLabel { color:white; font-size:11px; }"
            )

    def mousePressEvent(self, event):
        # 左鍵加點
        if event.button() == Qt.LeftButton:
            self.inc_cb(self.code)
        # 右鍵減點
        elif event.button() == Qt.RightButton:
            self.dec_cb(self.code)

        # 可以選擇要不要呼叫父類別實作
        # super().mousePressEvent(event)


# =========================================================
# SkillTreeGrid：用 GridLayout 排技能
# =========================================================
SKILL_PER_ROW = 7  # 一排 7 個

class SkillTreeGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(12)

    def clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def set_tree(self, skill_map_job, levels, job_chain, inc_cb, dec_cb):
        """
        skill_map_job: { skill_code -> skill_info }
        levels:        { skill_code -> lv }
        job_chain:     ['Swordman', 'Knight', 'Knight_H', 'Rune_Knight', ...]
        """
        self.clear()
        if not skill_map_job:
            return

        placed = set()
        row_offset = 0

        # ---------- 1) 先把 job_chain 分成「職業群組」 ----------
        # 例如: ['Swordman', 'Knight', 'Knight_H', 'Rune_Knight']
        # -> groups = [
        #      ['Swordman'],
        #      ['Knight','Knight_H'],
        #      ['Rune_Knight'],
        #    ]
        groups: list[list[str]] = []
        i = 0
        while i < len(job_chain):
            cur = job_chain[i]
            if i + 1 < len(job_chain):
                nxt = job_chain[i + 1]
                # 判斷 Knight + Knight_H 這種組合
                if nxt.endswith("_H") and nxt[:-2] == cur:
                    groups.append([cur, nxt])
                    i += 2
                    continue
            groups.append([cur])
            i += 1

        # ---------- 2) 逐個群組往下堆疊 ----------
        for idx_group, group in enumerate(groups):
            # 合併這個群組所有職業頁面的位置表
            # combined_pos: { skill_code -> index }
            combined_pos: dict[str, int] = {}
            for job_name in group:
                pos_map = treeview_positions.get(job_name, {})
                if not pos_map:
                    continue
                # 後出現的職業可以覆蓋前面的 index（例如 Knight_H 想調整部分技能位置）
                for code, idx in pos_map.items():
                    if code in skill_map_job:  # 只排在本職業 skill tree 有的技能
                        combined_pos[code] = idx

            if not combined_pos:
                continue

            # 拿出 index 與 code，並排序
            codes_with_idx = sorted(combined_pos.items(), key=lambda x: x[1])
            max_idx = max(idx for _, idx in codes_with_idx)
            max_local_row = max_idx // SKILL_PER_ROW

            # ---------- 2-1) 排這個群組的所有技能 ----------
            for code, idx in codes_with_idx:
                if code in placed:
                    continue
                info   = skill_map_job[code]
                max_lv = info.get("MaxLevel", 0)

                row_local = idx // SKILL_PER_ROW
                col       = idx %  SKILL_PER_ROW
                row       = row_offset + row_local

                node = SkillNodeWidget(
                    code,
                    get_level=lambda c, lv=levels: lv.get(c, 0),
                    max_level=max_lv,
                    inc_cb=inc_cb,
                    dec_cb=dec_cb,
                )
                self.grid.addWidget(node, row, col)
                placed.add(code)

            # 這個群組使用的總行數 = max_local_row + 1
            row_offset += max_local_row + 1

            # ---------- 2-2) 群組之間插分隔線 ----------
            if idx_group < len(groups) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("color: #666;")
                self.grid.addWidget(line, row_offset, 0, 1, SKILL_PER_ROW)
                row_offset += 1

        # ---------- 3) 把沒出現在任何職業頁面裡的技能丟最後 ----------
        remaining = [code for code in skill_map_job.keys() if code not in placed]
        if remaining:
            if row_offset > 0:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("color: #666;")
                self.grid.addWidget(line, row_offset, 0, 1, SKILL_PER_ROW)
                row_offset += 1

            for i, code in enumerate(sorted(remaining)):
                info   = skill_map_job[code]
                max_lv = info.get("MaxLevel", 0)
                row    = row_offset + i // SKILL_PER_ROW
                col    = i % SKILL_PER_ROW

                node = SkillNodeWidget(
                    code,
                    get_level=lambda c, lv=levels: lv.get(c, 0),
                    max_level=max_lv,
                    inc_cb=inc_cb,
                    dec_cb=dec_cb,
                )
                self.grid.addWidget(node, row, col)
                placed.add(code)



    def refresh_levels(self, skill_map_job, levels):
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, SkillNodeWidget):
                info = skill_map_job.get(w.code, {})
                w.max_level = info.get("MaxLevel", 0)
                w.update_display()

# =========================================================
# 主視窗
# =========================================================
class SkillTreeWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RO Skill Tree - Grid 模式")
        self.resize(900, 600)

        self.current_job_key = None
        self.current_skill_map_job = {}
        self.current_levels = {}
        # 新增：反向依賴表  { 前置技能code -> [依賴它的技能code, ...] }
        self.dependents = {}
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 職業選單
        top_row = QHBoxLayout()
        main_layout.addLayout(top_row)
        top_row.addWidget(QLabel("選擇職業 (id_jobneme)："))

        self.job_combo = QComboBox()
        self.job_combo.addItem("-- 請選擇 --", userData=None)
        for jid, job in job_dict.items():
            key = job["id_jobneme"]
            if key not in job_skill_tree_raw:
                continue
            text = f'{job["name"]} ({key})'
            self.job_combo.addItem(text, userData=key)
        self.job_combo.currentIndexChanged.connect(self.on_job_changed)
        top_row.addWidget(self.job_combo, 1)

        # 滾動區包 SkillTreeGrid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.tree_widget = SkillTreeGrid()
        self.scroll.setWidget(self.tree_widget)
        main_layout.addWidget(self.scroll)

        

    # ---- 切換職業 ----
    def on_job_changed(self, idx):
        key = self.job_combo.itemData(idx)
        if key is None:
            self.current_job_key = None
            self.current_skill_map_job = {}
            self.current_levels = {}
            self.dependents = {}
            self.tree_widget.clear()
            return

        self.current_job_key = key
        self.current_skill_map_job = build_job_skill_map(key)
        self.current_levels = {code: 0 for code in self.current_skill_map_job.keys()}

        # 建依賴表（你原本就有）
        self.dependents = {code: [] for code in self.current_skill_map_job.keys()}
        for code, info in self.current_skill_map_job.items():
            for r in info.get("Requires", []) or []:
                parent = r.get("Name")
                if parent in self.dependents:
                    self.dependents[parent].append(code)

        # ★ 取得這條職業線：1轉/2轉/3轉/4轉
        job_chain = get_job_chain(key)
        self.tree_widget.set_tree(
            self.current_skill_map_job,
            self.current_levels,
            job_chain,
            inc_cb=self.increase_skill,
            dec_cb=self.decrease_skill,
        )



    #自動補滿前置技能
    def auto_fill_prerequisites(self, code: str):
        """
        遞迴確保某技能的所有前置都達到需求等級。
        能補的就補，不行的就跳過，不會阻擋加點。
        直接修改 self.current_levels。
        """
        info = self.current_skill_map_job.get(code)
        if not info:
            return

        requires = info.get("Requires", []) or []
        for r in requires:
            p_code = r.get("Name")
            req_lv = r.get("Level", 1)
            if not p_code:
                continue

            # 先處理前置技能自己的前置
            self.auto_fill_prerequisites(p_code)

            parent_info = self.current_skill_map_job.get(p_code)
            if not parent_info:
                # 這個前置技能不在當前職業的 skill list（可能是前一轉技能）
                # UI 無法幫你加，就略過，不要整個失敗
                continue

            max_lv_parent = parent_info.get("MaxLevel", 0)
            if max_lv_parent <= 0:
                # 無法加點的技能，略過
                continue

            # 要求等級不要超過 MaxLevel
            req_lv = min(req_lv, max_lv_parent)

            cur_lv_parent = self.current_levels.get(p_code, 0)
            if cur_lv_parent < req_lv:
                self.current_levels[p_code] = req_lv



    # ---- 加點----
    def increase_skill(self, code: str):
        info = self.current_skill_map_job.get(code)
        if not info:
            return

        max_lv = info.get("MaxLevel", 0)
        cur_lv = self.current_levels.get(code, 0)
        if cur_lv >= max_lv:
            #QMessageBox.information(self, "已達上限", f"{code} 已達最大等級。")
            return

        # ★ 先自動補滿前置技能（不看回傳值，能補的都補）
        self.auto_fill_prerequisites(code)

        # 再確認自己還沒超過上限，然後加 1 等
        cur_lv = self.current_levels.get(code, 0)
        if cur_lv >= max_lv:
            #QMessageBox.information(self, "已達上限", f"{code} 已達最大等級。")
            return

        self.current_levels[code] = cur_lv + 1

        # 更新畫面
        self.tree_widget.refresh_levels(self.current_skill_map_job, self.current_levels)


    #存在且沒超過 MaxLevel
    def can_increase_skill(self, code: str) -> bool:
        info = self.current_skill_map_job.get(code)
        if not info:
            return False
        cur = self.current_levels.get(code, 0)
        max_lv = info.get("MaxLevel", 0)
        return cur < max_lv


    #連鎖清除不符合前置的技能
    def cascade_invalidate(self, code: str, visited=None):
        """
        某技能等級變低後，檢查其所有後繼技能；
        若不滿足前置要求，該技能歸 0，並且繼續往下一層傳遞。
        """
        if visited is None:
            visited = set()
        if code in visited:
            return
        visited.add(code)

        for dep in self.dependents.get(code, []):
            info = self.current_skill_map_job.get(dep)
            if not info:
                continue

            requires = info.get("Requires", []) or []
            ok = True
            for r in requires:
                p_code = r.get("Name")
                req_lv = r.get("Level", 1)
                if not p_code:
                    continue
                if self.current_levels.get(p_code, 0) < req_lv:
                    ok = False
                    break

            if not ok and self.current_levels.get(dep, 0) > 0:
                # 不符合前置 → 歸 0，並繼續往下清
                self.current_levels[dep] = 0
                self.cascade_invalidate(dep, visited)

    # ---- 減點----
    def decrease_skill(self, code: str):
        cur = self.current_levels.get(code, 0)
        if cur <= 0:
            return

        # 先自己減 1
        self.current_levels[code] = cur - 1

        # ★ 檢查所有依賴這個技能的後續技能
        self.cascade_invalidate(code)

        # 更新畫面
        self.tree_widget.refresh_levels(self.current_skill_map_job, self.current_levels)



# =========================================================
# main
# =========================================================
def main():
    load_skill_map()       # 讀 skillneme.csv
    load_skill_tree()      # 讀 skill_tree.yml
    load_skill_treeview()  # ★ 新增：讀 skilltreeview.lub

    app = QApplication(sys.argv)
    win = SkillTreeWindow()
    win.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
