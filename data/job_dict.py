
#6大12分支職業點數 "point":"49/49/20/69/54"
#貓 ,"point":"59/54"
#超初 ,"point":"98/69/54"
#槍手忍者 ,"point":"69/69/54"
#704天帝 ,"point":"49/49/69/54"


#職業名稱跟JOB補正#ROCalculator
job_dict = {
    0: {"id": "","id_jobneme": "","id_jobneme_OL": "","selectskill": "", "name": "", "TJobMaxPoint": [0,0,0,0,0,0,0,0,0,0,0,0],"point":"0"},
    4252: {"id": "RK","id_jobneme": "Dragon_Knight","id_jobneme_OL": "Swordman/Knight/Knight_H/Rune_Knight","selectskill": "RK/DK", "name": "盧恩龍爵", "TJobMaxPoint": [6,8,7,8,8,6,10,6,3,5,6,8],"point":"49/49/20/69/54"},
    4253: {"id": "ME","id_jobneme": "Meister","id_jobneme_OL": "Merchant/Blacksmith/Blacksmith_H/Mechanic","selectskill": "NC/MT", "name": "機甲神匠", "TJobMaxPoint": [10,6,10,6,5,6,9,10,5,0,7,7],"point":"49/49/20/69/54"},
    4254: {"id": "GX","id_jobneme": "Shadow_Cross","id_jobneme_OL": "Thief/Assassin/Assassin_H/Guillotine_Cross","selectskill": "GC/ASC/SHC", "name": "十字影武", "TJobMaxPoint": [8,11,6,5,9,4,12,8,4,0,7,7],"point":"49/49/20/69/54"},
    4255: {"id": "WL","id_jobneme": "Arch_Mage","id_jobneme_OL": "Magician/Wizard/Wizard_H/Warlock","selectskill": "WL/AG", "name": "禁咒魔導士", "TJobMaxPoint": [1,7,8,15,8,4,0,8,7,13,9,1],"point":"49/49/20/69/54"},
    4256: {"id": "AB","id_jobneme": "Cardinal","id_jobneme_OL": "Acolyte/Priest/Priest_H/Archbishop","selectskill": "AB/CD", "name": "樞機主教", "TJobMaxPoint": [6,7,7,12,7,4,8,5,5,9,4,7],"point":"49/49/20/69/54"},
    4257: {"id": "RA","id_jobneme": "Windhawk","id_jobneme_OL": "Archer/Hunter/Hunter_H/Ranger","selectskill": "SN/RA/WH", "name": "風鷹狩獵者", "TJobMaxPoint": [2,12,8,9,8,4,9,5,5,4,11,4],"point":"49/49/20/69/54"},
    4258: {"id": "RG","id_jobneme": "Imperial_Guard","id_jobneme_OL": "Swordman/Crusader/Crusader_H/Royal_Guard","selectskill": "LG/PA/IG", "name": "帝國聖衛軍", "TJobMaxPoint": [9,3,9,10,9,3,7,11,6,7,4,3],"point":"49/49/20/69/54"},
    4259: {"id": "GE","id_jobneme": "Biolo","id_jobneme_OL": "Merchant/Alchemist/Alchemist_H/Genetic","selectskill": "GN/CR/BO", "name": "生命締造者", "TJobMaxPoint": [5,6,8,12,8,4,7,4,4,4,7,12],"point":"49/49/20/69/54"},
    4260: {"id": "SC","id_jobneme": "Abyss_Chaser","id_jobneme_OL": "Thief/Rogue/Rogue_H/Shadow_Chaser","selectskill": "SC/ABC", "name": "深淵追跡者", "TJobMaxPoint": [8,9,8,6,6,6,8,8,4,7,5,6],"point":"49/49/20/69/54"},
    4261: {"id": "SO","id_jobneme": "Elemental_Master","id_jobneme_OL": "Magician/Sage/Sage_H/Sorcerer","selectskill": "SO/EM", "name": "元素支配者", "TJobMaxPoint": [4,4,8,13,9,5,3,8,7,12,5,3],"point":"49/49/20/69/54"},
    4262: {"id": "SU","id_jobneme": "Inquisitor","id_jobneme_OL": "Acolyte/Monk/Monk_H/Sura","selectskill": "MO/SR/IQ", "name": "聖裁者", "TJobMaxPoint": [10,10,6,8,8,1,11,8,5,3,5,6],"point":"49/49/20/69/54"},
    4263: {"id": "MI","id_jobneme": "Troubadour","id_jobneme_OL": "Archer/Bard/Bard_H/Minstrel","selectskill": "CG/WM/TR", "name": "天籟頌者", "TJobMaxPoint": [7,7,7,9,10,3,6,7,4,6,11,4],"point":"49/49/20/69/54"},
    4264: {"id": "WA","id_jobneme": "Trouvere","id_jobneme_OL": "Archer/Dancer/Dancer_H/Wanderer","selectskill": "CG/WM/TR", "name": "樂之舞靈", "TJobMaxPoint": [7,9,6,10,8,3,6,7,4,6,11,4],"point":"49/49/20/69/54"},
    4308: {"id": "SUM","id_jobneme": "Spirit_Handler","id_jobneme_OL": "Do_Summoner","selectskill": "SU/SH", "name": "魂靈師", "TJobMaxPoint": [5,7,5,9,12,5,8,6,5,8,7,4],"point":"59/54"},
    4307: {"id": "SN","id_jobneme": "Hyper_Novice","id_jobneme_OL": "Supernovice/Supernovice2","selectskill": "HN", "name": "終極初學者", "TJobMaxPoint": [10,5,6,10,5,6,9,5,4,9,8,3],"point":"98/69/54"},
    4306: {"id": "RE","id_jobneme": "Night_Watch","id_jobneme_OL": "Gunslinger/Rebellion","selectskill": "RL/NW", "name": "夜行者", "TJobMaxPoint": [3,8,6,8,11,7,11,6,5,0,10,5],"point":"69/69/54"},
    4304: {"id": "OB","id_jobneme": "Shinkiro","id_jobneme_OL": "Ninja/Kagerou","selectskill": "NJ/KO/SS", "name": "流浪忍者", "TJobMaxPoint": [10,12,6,4,9,3,10,10,4,0,6,8],"point":"69/69/54"},
    4305: {"id": "KO","id_jobneme": "Shiranui","id_jobneme_OL": "Ninja/Oboro","selectskill": "NJ/KO/SS", "name": "疾風忍者", "TJobMaxPoint": [4,8,5,10,10,3,4,8,10,3,6,7],"point":"69/69/54"},
    4303: {"id": "SL","id_jobneme": "Soul_Ascetic","id_jobneme_OL": "Taekwon/Linker/Soul_Reaper","selectskill": "SP/SOA", "name": "契靈士", "TJobMaxPoint": [3,7,7,11,13,2,0,8,7,16,7,3],"point":"49/49/69/54"},
    4302: {"id": "SE","id_jobneme": "Sky_Emperor","id_jobneme_OL": "Taekwon/Star/Star_Emperor","selectskill": "TK/SJ/SKE", "name": "天帝", "TJobMaxPoint": [12,10,6,3,9,3,12,10,2,0,6,7],"point":"49/49/69/54"},
}
