# 額外參數對照表
all_skill_entries = {#範例[    "": {"type": "技能/料理","code":["",""]},

    #15料
    "力量棒棒條": {"type": "料理","code":["AddExtParam(0,103,15)"]},
    "敏捷棒棒條": {"type": "料理","code":["AddExtParam(0,104,15)"]},
    "體力棒棒條": {"type": "料理","code":["AddExtParam(0,105,15)"]},
    "智慧棒棒條": {"type": "料理","code":["AddExtParam(0,106,15)"]},
    "靈巧棒棒條": {"type": "料理","code":["AddExtParam(0,107,15)"]},
    "幸運棒棒條": {"type": "料理","code":["AddExtParam(0,108,15)"]},
    #20料
    "烤野豬": {"type": "料理","code":["AddExtParam(0,103,20)"]},
    "捕蟲藥草煎": {"type": "料理","code":["AddExtParam(0,104,20)"]},
    "米洛斯燒肉": {"type": "料理","code":["AddExtParam(0,105,20)"]},
    "狼血雞尾酒": {"type": "料理","code":["AddExtParam(0,106,20)"]},
    "小雪獸冰茶": {"type": "料理","code":["AddExtParam(0,107,20)"]},
    "畢帝特龍尾麵": {"type": "料理","code":["AddExtParam(0,108,20)"]},
    #櫻花
    #"蒙布朗蛋糕": {"type": "料理","code":["AddMDamage_Size(1, 0, 15)","AddMDamage_Size(1, 1, 15)","AddMDamage_Size(1, 2, 15)"]},
    #"櫻花年糕": {"type": "料理","code":["AddMDamage_Property(1, 10, 10)"]},
    #"豐滿花樹枝": {"type": "料理","code":["AddSkillMDamage(10, 10)"]},
    #學術節料理
    "學術節米餅": {"type": "料理","code":["AddMDamage_Size(1, 0, 10)","AddMDamage_Size(1, 1, 10)","AddMDamage_Size(1, 2, 10)","AddDamage_Size(1, 0, 10)","AddDamage_Size(1, 1, 10)","AddDamage_Size(1, 2, 10)","AddExtParam(1, 239, 15)"]},
    "學術節餅乾": {"type": "料理","code":["AddMeleeAttackDamage(1, 12)","AddRangeAttackDamage(1,  12)","AddSkillMDamage(10, 12)","AddExtParam(1, 50, 30)"]},
    "學術節即溶咖啡": {"type": "料理","code":["AddExtParam(1, 207, 15)","AddExtParam(1, 140, 15)","SubSpellCastTime(10)"]},
    "祕密文件": {"type": "料理","code":["AddExtParam(1, 49, 0)","AddMDamage_Property(1, 10, 10)","AddDamage_Property(1, 10, 10)"]},

    "高級戰鬥藥": {"type": "料理","code":["AddExtParam(1, 140, 10)"]},
    "魔力藥水": {"type": "料理","code":["AddExtParam(1, 200, 50)"]},
    "藍色藥草活化液": {"type": "料理","code":["AddSkillMDamage(10, 10)"]},
    "戰神蒂爾之祝福": {"type": "料理","code":["AddExtParam(1, 200, 20)"]},

    #====技能
    "慈悲術": {"type": "技能","code": ["temp = 70 / 10","AddExtParam(0,103,10 + math.floor(temp / 2))","AddExtParam(0,106,10 + math.floor(temp / 2)","AddExtParam(0,107,10 + math.floor(temp / 2)","AddExtParam(0,49,20)"]},
    "純白百合花": {"type": "技能","code":["temp = 70 / 10","AddExtParam(0,104,12 + math.floor(temp / 2))","AddExtParam(0,167,10 + math.floor(temp / 2))"]},
    "神聖權能": {"type": "技能","code":["AddExtParam(1, 242, 50)","AddExtParam(1, 243, 50)"]},
    "五行符": {"type": "技能","code":["AddMDamage_Property(1, 0, 20)","AddMDamage_Property(1, 1, 20)","AddMDamage_Property(1,2, 20)","AddMDamage_Property(1, 3, 20)","AddMDamage_Property(1, 4, 20)","AddDamage_Property(1, 0, 20)","AddDamage_Property(1, 1, 20)","AddDamage_Property(1,2, 20)","AddDamage_Property(1, 3, 20)","AddDamage_Property(1, 4, 20)"]},
    "武士符": {"type": "技能","code":["AddExtParam(1, 242, 10)"]},
    "隼鷹靈魂": {"type": "技能","code":["AddExtParam(1, 41, 50)"]},
    "法師符": {"type": "技能","code":["AddExtParam(1, 243, 10)"]},
    "精靈靈魂": {"type": "技能","code":["AddExtParam(1, 200, 50)"]},
    "天地神靈": {"type": "技能","code":["AddMeleeAttackDamage(1, 25)","AddRangeAttackDamage(1, 25)","AddSkillMDamage(10, 25)"]},
}
