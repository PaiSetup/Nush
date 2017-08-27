cd ../
for /f "tokens=*" %%G in (devices.txt) do (
	echo %%G
	cd nircmd
	nircmd.exe setdefaultsounddevice "%%G" 1 
	nircmd.exe setdefaultsounddevice "%%G" 2
	goto label
)
:label

cd ../scripts
@echo %active% > active.txt