import os
import csv
import configparser
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import qrcode
import barcode
from barcode.writer import ImageWriter

class ConfigLoader:
    def __init__(self, config_file='config/config.ini'):
        self.config = configparser.ConfigParser()
        self.load_config(config_file)

    def load_config(self, config_file):
        try:
            self.config.read(config_file)
        except configparser.Error as e:
            print(f"Error reading config file {config_file}: {e}")
            raise

    def get(self, section, option):
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            print(f"Configuration error: {e}")
            raise

    def get_tuple(self, section, option):
        try:
            value_str = self.get(section, option)
            return tuple(map(int, value_str.split(',')))
        except ValueError as e:
            print(f"Error parsing tuple from config: {e}")
            raise

    def get_int(self, section, option):
        try:
            return self.config.getint(section, option)
        except ValueError as e:
            print(f"Error parsing int from config: {e}")
            raise

    def get_boolean(self, section, option):
        try:
            return self.config.getboolean(section, option)
        except ValueError as e:
            print(f"Error parsing boolean from config: {e}")
            raise

class ImageProcessor:
    @staticmethod
    def resize_image(image, size):
        try:
            return image.resize(size, Image.LANCZOS)
        except Exception as e:
            print(f"Error resizing image: {e}")
            raise

    @staticmethod
    def draw_multiline_text(draw, text, position, font, line_height):
        lines = text.split('\n')
        x, y = position
        for line in lines:
            try:
                draw.text((x, y), line, fill="black", font=font)
                y += line_height
            except Exception as e:
                print(f"Error drawing text: {e}")
                raise

    @staticmethod
    def generate_qr_code(data, size):
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill='black', back_color='white')
            return ImageProcessor.resize_image(qr_img, size)
        except Exception as e:
            print(f"Error generating QR code: {e}")
            raise

    @staticmethod
    def generate_barcode(data, size):
        try:
            ean = barcode.get('ean13', data, writer=ImageWriter())
            barcode_img = ean.render()
            return ImageProcessor.resize_image(barcode_img, size)
        except Exception as e:
            print(f"Error generating barcode: {e}")
            raise

class ShippingLabelGenerator:
    def __init__(self, config):
        self.config = config
        self.master_image_path = self.config.get('Paths', 'master_shipping_label_image_path')
        self.font_path = self.config.get('Paths', 'font_path')
        self.output_folder = self.config.get('Paths', 'output_folder')
        self.csv_file_path = self.config.get('Paths', 'csv_file_path')

        self.qr_position = self.config.get_tuple('Positions', 'qr_position')
        self.barcode_position = self.config.get_tuple('Positions', 'barcode_position')
        self.text_position = self.config.get_tuple('Positions', 'text_position')

        self.qr_size = self.config.get_tuple('Sizes', 'qr_size')
        self.barcode_size = self.config.get_tuple('Sizes', 'barcode_size')

        self.font_size = self.config.get_int('Font', 'font_size')

        self.clear_output_folder = self.config.get_boolean('Settings', 'clear_output_folder')

        self.font = self.load_font()
        self.line_height = self.font.getbbox("A")[3] + 2

        self.master_image = self.load_master_image()

        self.prepare_output_folder()

    def load_font(self):
        try:
            return ImageFont.truetype(self.font_path, self.font_size)
        except IOError as e:
            print(f"Error loading font {self.font_path}: {e}")
            raise

    def load_master_image(self):
        try:
            return Image.open(self.master_image_path)
        except (FileNotFoundError, UnidentifiedImageError) as e:
            print(f"Error loading master image {self.master_image_path}: {e}")
            raise

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)
        if self.clear_output_folder:
            for filename in os.listdir(self.output_folder):
                file_path = os.path.join(self.output_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        os.rmdir(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

    def create_shipping_label(self, row):
        try:
            qr_data = row['qr_data']
            barcode_data = row['barcode_data']
            multiline_text = row['multiline_text'].replace('\\n', '\n')

            qr_img = ImageProcessor.generate_qr_code(qr_data, self.qr_size)
            barcode_img = ImageProcessor.generate_barcode(barcode_data, self.barcode_size)

            label_with_codes = self.master_image.copy()
            draw = ImageDraw.Draw(label_with_codes)

            label_with_codes.paste(qr_img, self.qr_position)
            label_with_codes.paste(barcode_img, self.barcode_position)
            ImageProcessor.draw_multiline_text(draw, multiline_text, self.text_position, self.font, self.line_height)

            output_filename = os.path.join(self.output_folder, f"{barcode_data}.png")
            label_with_codes.save(output_filename)
            print(f"QR code and barcode embedded successfully in {output_filename}.")
        except Exception as e:
            print(f"Error creating shipping label: {e}")
            raise

    def csv_row_generator(self):
        try:
            with open(self.csv_file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    yield row
        except FileNotFoundError as e:
            print(f"Error opening CSV file {self.csv_file_path}: {e}")
            raise
        except csv.Error as e:
            print(f"Error reading CSV file {self.csv_file_path}: {e}")
            raise

    def process_csv(self):
        try:
            for row in self.csv_row_generator():
                self.create_shipping_label(row)
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            raise

def main():
    try:
        config_loader = ConfigLoader()
        label_generator = ShippingLabelGenerator(config_loader)
        label_generator.process_csv()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
