# PSX Pixel

Chuyển tranh digital art thành pixel art kiểu PS1 ngay trên Windows: chuột phải vào ảnh trong Explorer, chọn style, bấm OK là xong.

- **Chuột phải ảnh** → *PSX Pixel ▸ Chuyển sang pixel PSX…* → chọn style → **OK**. Chọn nhiều ảnh cùng lúc cũng được, tất cả mở chung một cửa sổ.
- **Chuột phải thư mục** (hoặc nền trống trong thư mục) → chuyển tất cả ảnh trong đó.
- **Xem trước** ảnh gốc, ảnh kết quả, hoặc so sánh hai ảnh cạnh nhau. Kết quả cập nhật ngay khi kéo thanh chỉnh.
- **5 style có sẵn**: PSX Dunmorn, PSX Sodium, Anime 90s, Giữ màu gốc, Game Boy. Tự lưu style riêng bằng nút *Lưu thành style mới…*.
- **Bảng màu**: có sẵn hoặc file `.hex` tải từ [Lospec](https://lospec.com/palette-list).
- **Kéo thả** ảnh hoặc thư mục vào cửa sổ. Mở app từ Start Menu, Desktop hoặc ghim lên Taskbar.
- **Tự cập nhật** từ GitHub (hỏi trước khi cập nhật).

Ảnh mới được lưu cạnh ảnh gốc, tên có đuôi `_psx.png`. Ảnh gốc không bị thay đổi.

## Cài đặt

Mở **PowerShell** và chạy:

```powershell
irm https://raw.githubusercontent.com/virtualman209/PSXPixel/main/setup.ps1 | iex
```

Tool được cài vào `%LOCALAPPDATA%\PSXPixel`, tạo lối tắt trên Start Menu và Desktop. Nếu máy chưa có Python 3, script sẽ tự cài qua `winget`. Thư viện Pillow và NumPy được cài tự động.

Cài không qua PowerShell: trên trang repo bấm *Code → Download ZIP*, giải nén ở đâu cũng được rồi chạy `install.bat`.

**Ghim lên Taskbar:** mở Start → tìm *PSX Pixel* → chuột phải → *Pin to taskbar*.

> Windows 11: chuột phải file → *Show more options* (hoặc Shift + chuột phải) mới thấy menu PSX Pixel.

Gỡ cài đặt: chạy `uninstall.bat` trong thư mục cài đặt, rồi xoá thư mục.

## Các thông số

| Thông số | Tác dụng |
| --- | --- |
| Chiều cao pixel | Chiều cao thật của pixel art. Càng thấp càng thô (gợi ý 128–200 cho portrait) |
| Bảng màu | Bảng có sẵn, *Tự động* (rút từ tranh, chỉnh *Số màu*), hoặc file `.hex` |
| Dither | *Bayer*: chấm đều kiểu PS1. *Floyd-Steinberg*: mịn, tự nhiên. *Không dither*: mảng màu phẳng |
| Cường độ dither | Độ rõ của các chấm Bayer |
| Hạt nhiễu | Nhiễu kiểu màn hình CRT. 0 là tắt |
| Tương phản, bão hoà | Chỉnh trên ảnh gốc trước khi giảm màu |
| Ám màu | Phủ một màu lên toàn ảnh, ví dụ xám xanh của sương |
| Phóng to khi lưu | Lưu ảnh lớn gấp N lần, pixel vẫn sắc. Chọn x1 để lấy kích thước thật đưa vào Unity |

Style tự lưu nằm trong `styles.json` ở thư mục cài đặt. Khi cập nhật, file này được giữ nguyên.

## Phát hành bản mới

Sửa code → tăng số phiên bản ở dòng đầu `version.txt` (các dòng sau là ghi chú thay đổi) → push lên `main`. Máy đã cài sẽ được hỏi cập nhật trong vòng 6 tiếng.

Repo private vẫn dùng được: đặt token chỉ đọc (Contents: Read-only) vào `github_token.txt` trong thư mục cài đặt.

Nếu đặt tên repo khác `virtualman209/PSXPixel`, sửa tên repo ở `updater.py`, `setup.ps1`, `update.ps1` và lệnh cài trong README.
