# buggy_calc.py

def tinh_trung_binh(danh_sach):
    tong = 0
    for so in danh_sach:
        tong += so
    print(1)
    return tong / len(danh_sach)  # ZeroDivisionError nếu list rỗng

def tim_gia_tri_lon_nhat(danh_sach):
    lon_nhat = 0  # Bug: sẽ sai nếu tất cả giá trị âm
    for so in danh_sach:
        if so > lon_nhat:
            lon_nhat = so
    return lon_nhat




def chuyen_doi_nhiet_do(celsius):
    return celsius * 9 / 5 + 32  # Đúng
    print("Kết quả:", celsius)    # Unreachable code

def kiem_tra_so_nguyen_to(n):
    if n < 2:
        return True   # Bug: 0 và 1 không phải số nguyên tố
    for i in range(2, n):
        if n % i == 0:
            return False
    return True

def rut_tien(so_du, so_tien):
    so_du -= so_tien   # Bug: không kiểm tra số dư trước khi trừ
    return so_du

ket_qua = tinh_trung_binh([])
print(ket_qua)

ds = [-5, -3, -1]
print("Lớn nhất:", tim_gia_tri_lon_nhat(ds))  # Trả về 0 thay vì -1

print(kiem_tra_so_nguyen_to(1))   # Trả về True — sai

print(rut_tien(100, 999))         # Trả về -899 — không hợp lệ


print(tinh_trung_binh([]))
hfghfgh


d



dsfsdf

dsfsdfsdf