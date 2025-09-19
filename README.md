# llmse-photo-watermark

一个简单的命令行工具：读取图片(或目录内所有图片)的 EXIF 拍摄时间(取年月日)作为文本水印，按指定位置/字号/颜色绘制到图片上，并输出到“原目录名_watermark”子目录中。

- 输入：图片文件路径或图片所在目录路径。
- EXIF 时间键优先顺序：DateTimeOriginal(36867) > DateTime(306)。格式按 EXIF“YYYY:MM:DD HH:MM:SS”，取“YYYY-MM-DD”。
- 支持选项：字体大小、颜色(HEX 或常见颜色名)、位置(top-left/top-right/center/bottom-left/bottom-right)、可选字体文件。
- 输出：在原始目录下创建“原目录名_watermark”子目录，并保持文件名不变输出水印图。

## 快速开始

1) 安装依赖
- 需要 Python 3.9+
- 安装 Pillow

```
pip install -r requirements.txt
```

2) 运行

```
python watermark_cli.py <路径> [--font-size 80] [--color "#FFFFFF"] [--position bottom-right] [--font-path <ttf路径>]
```

## 参数说明

- `<路径>`：
  - 传入单个图片文件路径：仅处理该文件；
  - 传入目录路径：递归处理其中常见图片( jpg/jpeg/png/tif/tiff )。
- `--font-size`：字体大小(像素)。默认 36。
- `--color`：
  - HEX，如“#FFFFFF”“#80FF0000”(支持含 alpha 的 #AARRGGBB 及 #RRGGBBAA)；
  - 或常见颜色名(white, red, black等)。
- `--position`：水印位置：top-left/top-right/center/bottom-left/bottom-right。默认 bottom-right。
- `--font-path`：可选 TrueType 字体文件路径；未指定时尝试使用 Pillow 自带的 DejaVuSans.ttf；若不可用则退回内置等宽字体。

## 示例

- 给单张图片加右下角白色水印，字号 40：

```
python watermark_cli.py D:\Photos\IMG_0001.JPG --font-size 40 --color "#FFFFFF" --position bottom-right
```

- 批量处理目录，使用自定义字体并放置左上角：

```
python watermark_cli.py D:\Photos --font-path C:\Windows\Fonts\arial.ttf --position top-left
```

## 注意

- 若图片无可用 EXIF 拍摄时间，将跳过并在终端提示。
- PNG 通常无 EXIF；JPEG/TIFF 更常见。
- 输出目录规则：
  - 若传入是文件 D:\Photos\IMG_0001.JPG，则输出至 D:\Photos\Photos_watermark\IMG_0001.JPG；
  - 若传入是目录 D:\Photos，则输出至 D:\Photos\Photos_watermark\...。
- 写入同名文件会覆盖旧输出文件。

## 许可证

MIT License，见 LICENSE。
