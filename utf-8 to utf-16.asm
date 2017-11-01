.686
.model flat
extern _ExitProcess@4 : PROC
extern _MessageBoxW@16 : PROC
extern __write : PROC 
public _main

.data
tab		db		0C4h, 85h,			; UTF-16: 0105h
				0EFh, 0BFh, 8Fh,	; UTF-16: FFCFh
				0F0h, 9Fh, 9Ah, 8Ch ; UTF-16: D83Dh, DE8Ch
				
tabLen	dd		$ - tab

.code

_convertSign PROC
	; array ptr in esi

	movzx	eax, byte ptr [esi]
	test	al, 10000000b
	jnz		NOT_ONE_BYTE
		; one byte
		mov		ebx, 1
		jmp		SUCCESS

	NOT_ONE_BYTE:
	test	al, 01000000b
	jz		ERROR
	test	al, 00100000b
	jnz		NOT_TWO_BYTE
		; two byte
		
		; load to word register (ax younger, bx older)
		movzx	bx, byte ptr [esi+1]

		; mask
		and		al, 00011111b
		and		bl, 00111111b

		; merge
		shl		ax, 6
		or		ax, bx

		; return
		mov		ebx, 2
		jmp		SUCCESS

	NOT_TWO_BYTE:
	test	al, 00010000b
	jnz		NOT_THREE_BYTE
		; three byte

		; load
		movzx	bx, byte ptr [esi+1]
		movzx	cx, byte ptr [esi+2]

		; mask
		and		al, 00001111b
		and		bl, 00111111b
		and		cl, 00111111b

		; merge
		shl		ax, 12
		shl		bx, 6
		or		ax, bx
		or		ax, cx

		; return
		mov		ebx, 3
		jmp		SUCCESS


	NOT_THREE_BYTE:
	test	al, 00001000b
	jnz		ERROR
		; four byte

		; load
		movzx	ebx, byte ptr [esi+1]
		movzx	ecx, byte ptr [esi+2]
		movzx	edx, byte ptr [esi+3]

		; mask
		and		al, 00000111b
		and		bl, 00111111b
		and		cl, 00111111b
		and		dl, 00111111b

		; merge
		shl		eax, 18
		shl		ebx, 12
		shl		ecx, 6
		or		eax, ebx
		or		eax, ecx
		or		eax, edx
		
		; subtract 10000h (clip to 20 bits)
		and		eax, 0FFFFFh
		
		; right word
		mov		cx, ax
		and		cx, 3FFh
		or		cx, 0DC00h

		; left word
		shr		eax, 10
		mov		bx, ax
		and		bx, 3FFh
		or		bx, 0DB00h

		; merge
		mov		ax, cx
		shl		eax, 16
		mov		ax, bx

		; return
		mov		ebx, 4
		jmp		SUCCESS


	ERROR:
		mov		eax, -1
		mov		ebx, -1
		ret

	SUCCESS:
		ret

_convertSign ENDP


_main PROC
	mov		esi, offset tab
	mov		edi, esi
	add		edi, tabLen
	LOOP_START:
		cmp		esi, edi
		jge		LOOP_END

		call	_convertSign

		add		esi, ebx
		jmp		LOOP_START
	LOOP_END:
	
	push	eax
	call	_ExitProcess@4
_main ENDP
END