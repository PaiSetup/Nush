echo off

::Get active device index
set active=0
for /f "tokens=1" %%G in (active.txt) do (
	set /a active=%%G
	goto label_1
)
:label_1
echo Active device index: %active%




::Get device count
set count=0
cd ../
for /f "tokens=*" %%G in (devices.txt) do (set /A count=count+1)
echo Device count: %count%




::Get next device number
set /a active = active+1
if /i %active% geq %count% (
	set /a active = 0
)
echo Next device index: %active%



::skip=0 doesn't work, hence 2 different loops
if %active% equ 0 (
	echo first
	for /f "tokens=*" %%G in (devices.txt) do (
		echo %%G
		cd nircmd
		nircmd.exe setdefaultsounddevice "%%G" 1 
		nircmd.exe setdefaultsounddevice "%%G" 2
		goto label_2
	)
) else ( 
	echo second
	for /f "tokens=* skip=%active%" %%G in (devices.txt) do (
		echo %%G
		cd nircmd
		nircmd.exe setdefaultsounddevice "%%G" 1 
		nircmd.exe setdefaultsounddevice "%%G" 2
		goto label_2
	)
)
:label_2

::update device index in active.txt
cd ../scripts
@echo %active% > active.txt