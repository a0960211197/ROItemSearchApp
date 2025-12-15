
	
[43] = {
	temp = GSklv(43)
	AddExtParam(1, 107, temp)
}

	
[134] = {
	temp = GSklv(134)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 16 then
		WeaponMasteryATK(temp * 3)
	end
}

[226] = {
	temp = GSklv(226)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 2 or temp_wp == 6 then
		WeaponMasteryATK(temp * 3)
	end
}

[248] = {
	temp = GSklv(248)
	AddExtParam(1, 109, temp * 200)
}
[274] = {
	temp = GSklv(274)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 15 then
		WeaponMasteryATK(temp * 10)
	end
}

[284] = {
	temp = GSklv(284)
	AddMdamage_Race(9,temp * 2)
	RaceAddDamage(9, temp * 4)
	if temp == 1 or temp == 2 then
		AddExtParam(1, 106, 1)
	end
	if temp == 3 or temp == 4 then
		AddExtParam(1, 106, 2)
	end
	if temp == 5 then
		AddExtParam(1, 106, 3)
	end

}

[315] = {
	temp = GSklv(315)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 13 or temp_wp == 14 then
		AddExtParam(1, 41, temp * 3)
		AddExtParam(1, 112, temp)
		AddExtParam(1, 167, temp)
	end
}

[2412] = {
	temp = GSklv(2412)
	AddExtParam(1, 110, temp * 30)
}
[2474] = {
	temp = GSklv(2474)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 2 then
		WeaponMasteryATK(temp * 10)
		AddExtParam(1, 49, temp)
	end
}



[5077] = {
	temp = GSklv(5077)
	AddExtParam(1, 200, temp * 20)
	AddExtParam(1, 109, temp * 400)
	AddExtParam(1, 110, temp * 40)
}

[5228] = {
	temp = GSklv(5228)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 23 then
		AddExtParam(1, 243, temp * 2)
	end
}

[5349] = {
	temp = GSklv(5349)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 13 or temp_wp == 14 then
		AddExtParam(1, 243, temp * 3)
		AddExtParam(1, 242, temp * 3)
	end
}




[5365] = {
	temp = GSklv(5365)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 15 then
		AddSkillMDamage(1, 1)
		AddSkillMDamage(2, 1)
		AddSkillMDamage(3, 1)
		AddSkillMDamage(4, 1)
		AddSkillMDamage(5, 1)
		AddSkillMDamage(1, temp * 1.4)
		AddSkillMDamage(2, temp * 1.4)
		AddSkillMDamage(3, temp * 1.4)
		AddSkillMDamage(4, temp * 1.4)
		AddSkillMDamage(5, temp * 1.4)
	end
}

[5416] = {
	temp = GSklv(5416)
	AddExtParam(1, 243, temp)
}
[5417] = {
	temp = GSklv(5417)
	AddExtParam(1, 237, temp)
}
[5450] = {
	temp = GSklv(5450)
	AddExtParam(1, 243, temp)
	AddDamage_passive_SKID(1, 5455, temp)
	AddDamage_passive_SKID(1, 5456, temp)
	AddDamage_passive_SKID(1, 5457, temp)
	AddDamage_passive_SKID(1, 5458, temp)
	AddDamage_passive_SKID(1, 5459, temp)
	AddDamage_passive_SKID(1, 5460, temp * 2)
}