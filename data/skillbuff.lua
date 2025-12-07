
	
[43] = {
	temp = GSklv(43)
	AddExtParam(1, 107, temp)
}

	
[134] = {
	temp = GSklv(134)
	WeaponMasteryATK(temp * 3)
}

[226] = {
	temp = GSklv(226)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 2 or temp_wp == 6 then
		WeaponMasteryATK(temp * 3)
}

[2474] = {
	temp = GSklv(2474)
	temp_wp = GetWeaponClass(4)
	if temp_wp == 2 then
		WeaponMasteryATK(temp * 10)
		AddExtParam(1, 49, temp)
}



[5077] = {
	temp = GSklv(5077)
	AddExtParam(1, 200, temp * 20)
	AddExtParam(1, 109, temp * 400)
	AddExtParam(1, 110, temp * 40)
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