# myapp/management/commands/seed.py

import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import requests
from worldtravel.models import Country, Region
from django.db import transaction

from django.conf import settings
        
media_root = settings.MEDIA_ROOT

def saveCountryFlag(country_code):
    flags_dir = os.path.join(media_root, 'flags')

    # Check if the flags directory exists, if not, create it
    if not os.path.exists(flags_dir):
        os.makedirs(flags_dir)

    # Check if the flag already exists in the media folder
    flag_path = os.path.join(flags_dir, f'{country_code}.png')
    if os.path.exists(flag_path):
        print(f'Flag for {country_code} already exists')
        return

    res = requests.get(f'https://flagcdn.com/h240/{country_code}.png')
    if res.status_code == 200:
        with open(flag_path, 'wb') as f:
            f.write(res.content)
        print(f'Flag for {country_code} downloaded')
    else:
        print(f'Error downloading flag for {country_code}')

class Command(BaseCommand):
    help = 'Imports the world travel data'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='Force import even if data already exists'
        )

    def handle(self, *args, **options):
        force = options['force']
        
        countries = [
            ('United States', 'us', 'NA'),
            ('Canada', 'ca', 'NA'),
            ('Mexico', 'mx', 'NA'),
            ('Brazil', 'br', 'SA'),
            ('Argentina', 'ar', 'SA'),
            ('United Kingdom', 'gb', 'EU'),
            ('Germany', 'de', 'EU'),
            ('France', 'fr', 'EU'),
            ('Japan', 'jp', 'AS'),
            ('China', 'cn', 'AS'),
            ('India', 'in', 'AS'),
            ('Australia', 'au', 'OC'),
            ('New Zealand', 'nz', 'OC'),
            ('South Africa', 'za', 'AF'),
            ('Egypt', 'eg', 'AF'),
            ('Sweden', 'se', 'EU'),
            ('Ireland', 'ie', 'EU'),
            ('Spain', 'es', 'EU'),
            ('Switzerland', 'ch', 'EU'),
            ('Italy', 'it', 'EU'),
            ('Iceland', 'is', 'EU'),
        ]
        
        regions = [
            ('US-AL', 'Alabama', 'us'),
            ('US-AK', 'Alaska', 'us'),
            ('US-AZ', 'Arizona', 'us'),
            ('US-AR', 'Arkansas', 'us'),
            ('US-CA', 'California', 'us'),
            ('US-CO', 'Colorado', 'us'),
            ('US-CT', 'Connecticut', 'us'),
            ('US-DE', 'Delaware', 'us'),
            ('US-FL', 'Florida', 'us'),
            ('US-GA', 'Georgia', 'us'),
            ('US-HI', 'Hawaii', 'us'),
            ('US-ID', 'Idaho', 'us'),
            ('US-IL', 'Illinois', 'us'),
            ('US-IN', 'Indiana', 'us'),
            ('US-IA', 'Iowa', 'us'),
            ('US-KS', 'Kansas', 'us'),
            ('US-KY', 'Kentucky', 'us'),
            ('US-LA', 'Louisiana', 'us'),
            ('US-ME', 'Maine', 'us'),
            ('US-MD', 'Maryland', 'us'),
            ('US-MA', 'Massachusetts', 'us'),
            ('US-MI', 'Michigan', 'us'),
            ('US-MN', 'Minnesota', 'us'),
            ('US-MS', 'Mississippi', 'us'),
            ('US-MO', 'Missouri', 'us'),
            ('US-MT', 'Montana', 'us'),
            ('US-NE', 'Nebraska', 'us'),
            ('US-NV', 'Nevada', 'us'),
            ('US-NH', 'New Hampshire', 'us'),
            ('US-NJ', 'New Jersey', 'us'),
            ('US-NM', 'New Mexico', 'us'),
            ('US-NY', 'New York', 'us'),
            ('US-NC', 'North Carolina', 'us'),
            ('US-ND', 'North Dakota', 'us'),
            ('US-OH', 'Ohio', 'us'),
            ('US-OK', 'Oklahoma', 'us'),
            ('US-OR', 'Oregon', 'us'),
            ('US-PA', 'Pennsylvania', 'us'),
            ('US-RI', 'Rhode Island', 'us'),
            ('US-SC', 'South Carolina', 'us'),
            ('US-SD', 'South Dakota', 'us'),
            ('US-TN', 'Tennessee', 'us'),
            ('US-TX', 'Texas', 'us'),
            ('US-UT', 'Utah', 'us'),
            ('US-VT', 'Vermont', 'us'),
            ('US-VA', 'Virginia', 'us'),
            ('US-WA', 'Washington', 'us'),
            ('US-WV', 'West Virginia', 'us'),
            ('US-WI', 'Wisconsin', 'us'),
            ('US-WY', 'Wyoming', 'us'),
            ('CA-AB', 'Alberta', 'ca'),
            ('CA-BC', 'British Columbia', 'ca'),
            ('CA-MB', 'Manitoba', 'ca'),
            ('CA-NB', 'New Brunswick', 'ca'),
            ('CA-NL', 'Newfoundland and Labrador', 'ca'),
            ('CA-NS', 'Nova Scotia', 'ca'),
            ('CA-ON', 'Ontario', 'ca'),
            ('CA-PE', 'Prince Edward Island', 'ca'),
            ('CA-QC', 'Quebec', 'ca'),
            ('CA-SK', 'Saskatchewan', 'ca'),
            ('CA-NT', 'Northwest Territories', 'ca'),
            ('CA-NU', 'Nunavut', 'ca'),
            ('CA-YT', 'Yukon', 'ca'),
            ('DE-BW', 'Baden-Württemberg', 'de'),
            ('DE-BY', 'Bayern', 'de'),
            ('DE-BE', 'Berlin', 'de'),
            ('DE-BB', 'Brandenburg', 'de'),
            ('DE-HB', 'Bremen', 'de'),
            ('DE-HH', 'Hamburg', 'de'),
            ('DE-HE', 'Hessen', 'de'),
            ('DE-MV', 'Mecklenburg-Vorpommern', 'de'),
            ('DE-NI', 'Niedersachsen', 'de'),
            ('DE-NW', 'Nordrhein-Westfalen', 'de'),
            ('DE-RP', 'Rheinland-Pfalz', 'de'),
            ('DE-SL', 'Saarland', 'de'),
            ('DE-SN', 'Sachsen', 'de'),
            ('DE-ST', 'Sachsen-Anhalt', 'de'),
            ('DE-SH', 'Schleswig-Holstein', 'de'),
            ('DE-TH', 'Thüringen', 'de'),
            ('FR-ARA', 'Auvergne-Rhône-Alpes', 'fr'),
            ('FR-BFC', 'Bourgogne-Franche-Comté', 'fr'),
            ('FR-BRE', 'Bretagne', 'fr'),
            ('FR-CVL', 'Centre-Val de Loire', 'fr'),
            ('FR-GES', 'Grand Est', 'fr'),
            ('FR-HDF', 'Hauts-de-France', 'fr'),
            ('FR-IDF', 'Île-de-France', 'fr'),
            ('FR-NOR', 'Normandy', 'fr'),
            ('FR-NAQ', 'Nouvelle-Aquitaine', 'fr'),
            ('FR-OCC', 'Occitanie', 'fr'),
            ('FR-PDL', 'Pays de la Loire', 'fr'),
            ('FR-PAC', 'Provence-Alpes-Côte d''Azur', 'fr'),
            ('FR-COR', 'Corsica', 'fr'),
            ('FR-MQ', 'Martinique', 'fr'),
            ('FR-GF', 'French Guiana', 'fr'),
            ('FR-RÉ', 'Réunion', 'fr'),
            ('FR-YT', 'Mayotte', 'fr'),
            ('FR-GP', 'Guadeloupe', 'fr'),
            ('GB-ENG', 'England', 'gb'),
            ('GB-NIR', 'Northern Ireland', 'gb'),
            ('GB-SCT', 'Scotland', 'gb'),
            ('GB-WLS', 'Wales', 'gb'),
            ('AR-C', 'Ciudad Autónoma de Buenos Aires', 'ar'),
            ('AR-B', 'Buenos Aires', 'ar'),
            ('AR-K', 'Catamarca', 'ar'),
            ('AR-H', 'Chaco', 'ar'),
            ('AR-U', 'Chubut', 'ar'),
            ('AR-W', 'Córdoba', 'ar'),
            ('AR-X', 'Corrientes', 'ar'),
            ('AR-E', 'Entre Ríos', 'ar'),
            ('AR-P', 'Formosa', 'ar'),
            ('AR-Y', 'Jujuy', 'ar'),
            ('AR-L', 'La Pampa', 'ar'),
            ('AR-F', 'La Rioja', 'ar'),
            ('AR-M', 'Mendoza', 'ar'),
            ('AR-N', 'Misiones', 'ar'),
            ('AR-Q', 'Neuquén', 'ar'),
            ('AR-R', 'Río Negro', 'ar'),
            ('AR-A', 'Salta', 'ar'),
            ('AR-J', 'San Juan', 'ar'),
            ('AR-D', 'San Luis', 'ar'),
            ('AR-Z', 'Santa Cruz', 'ar'),
            ('AR-S', 'Santa Fe', 'ar'),
            ('AR-G', 'Santiago del Estero', 'ar'),
            ('AR-V', 'Tierra del Fuego', 'ar'),
            ('AR-T', 'Tucumán', 'ar'),
            ('MX-AGU', 'Aguascalientes', 'mx'),
            ('MX-BCN', 'Baja California', 'mx'),
            ('MX-BCS', 'Baja California Sur', 'mx'),
            ('MX-CAM', 'Campeche', 'mx'),
            ('MX-CHP', 'Chiapas', 'mx'),
            ('MX-CHH', 'Chihuahua', 'mx'),
            ('MX-CMX', 'Ciudad de México', 'mx'),
            ('MX-COA', 'Coahuila de Zaragoza', 'mx'),
            ('MX-COL', 'Colima', 'mx'),
            ('MX-DUR', 'Durango', 'mx'),
            ('MX-GUA', 'Guanajuato', 'mx'),
            ('MX-GRO', 'Guerrero', 'mx'),
            ('MX-HID', 'Hidalgo', 'mx'),
            ('MX-JAL', 'Jalisco', 'mx'),
            ('MX-MIC', 'Michoacán de Ocampo', 'mx'),
            ('MX-MOR', 'Morelos', 'mx'),
            ('MX-MEX', 'México', 'mx'),
            ('MX-NAY', 'Nayarit', 'mx'),
            ('MX-NLE', 'Nuevo León', 'mx'),
            ('MX-OAX', 'Oaxaca', 'mx'),
            ('MX-PUE', 'Puebla', 'mx'),
            ('MX-QUE', 'Querétaro', 'mx'),
            ('MX-ROO', 'Quintana Roo', 'mx'),
            ('MX-SLP', 'San Luis Potosí', 'mx'),
            ('MX-SIN', 'Sinaloa', 'mx'),
            ('MX-SON', 'Sonora', 'mx'),
            ('MX-TAB', 'Tabasco', 'mx'),
            ('MX-TAM', 'Tamaulipas', 'mx'),
            ('MX-TLA', 'Tlaxcala', 'mx'),
            ('MX-VER', 'Veracruz de Ignacio de la Llave', 'mx'),
            ('MX-YUC', 'Yucatán', 'mx'),
            ('MX-ZAC', 'Zacatecas', 'mx'),
            ('JP-01', 'Hokkaido', 'jp'),
            ('JP-02', 'Aomori', 'jp'),
            ('JP-03', 'Iwate', 'jp'),
            ('JP-04', 'Miyagi', 'jp'),
            ('JP-05', 'Akita', 'jp'),
            ('JP-06', 'Yamagata', 'jp'),
            ('JP-07', 'Fukushima', 'jp'),
            ('JP-08', 'Ibaraki', 'jp'),
            ('JP-09', 'Tochigi', 'jp'),
            ('JP-10', 'Gunma', 'jp'),
            ('JP-11', 'Saitama', 'jp'),
            ('JP-12', 'Chiba', 'jp'),
            ('JP-13', 'Tokyo', 'jp'),
            ('JP-14', 'Kanagawa', 'jp'),
            ('JP-15', 'Niigata', 'jp'),
            ('JP-16', 'Toyama', 'jp'),
            ('JP-17', 'Ishikawa', 'jp'),
            ('JP-18', 'Fukui', 'jp'),
            ('JP-19', 'Yamanashi', 'jp'),
            ('JP-20', 'Nagano', 'jp'),
            ('JP-21', 'Gifu', 'jp'),
            ('JP-22', 'Shizuoka', 'jp'),
            ('JP-23', 'Aichi', 'jp'),
            ('JP-24', 'Mie', 'jp'),
            ('JP-25', 'Shiga', 'jp'),
            ('JP-26', 'Kyoto', 'jp'),
            ('JP-27', 'Osaka', 'jp'),
            ('JP-28', 'Hyogo', 'jp'),
            ('JP-29', 'Nara', 'jp'),
            ('JP-30', 'Wakayama', 'jp'),
            ('JP-31', 'Tottori', 'jp'),
            ('JP-32', 'Shimane', 'jp'),
            ('JP-33', 'Okayama', 'jp'),
            ('JP-34', 'Hiroshima', 'jp'),
            ('JP-35', 'Yamaguchi', 'jp'),
            ('JP-36', 'Tokushima', 'jp'),
            ('JP-37', 'Kagawa', 'jp'),
            ('JP-38', 'Ehime', 'jp'),
            ('JP-39', 'Kochi', 'jp'),
            ('JP-40', 'Fukuoka', 'jp'),
            ('JP-41', 'Saga', 'jp'),
            ('JP-42', 'Nagasaki', 'jp'),
            ('JP-43', 'Kumamoto', 'jp'),
            ('JP-44', 'Oita', 'jp'),
            ('JP-45', 'Miyazaki', 'jp'),
            ('JP-46', 'Kagoshima', 'jp'),
            ('JP-47', 'Okinawa', 'jp'),
            ('CN-BJ', 'Beijing', 'cn'),
            ('CN-TJ', 'Tianjin', 'cn'),
            ('CN-HE', 'Hebei', 'cn'),
            ('CN-SX', 'Shanxi', 'cn'),
            ('CN-NM', 'Inner Mongolia', 'cn'),
            ('CN-LN', 'Liaoning', 'cn'),
            ('CN-JL', 'Jilin', 'cn'),
            ('CN-HL', 'Heilongjiang', 'cn'),
            ('CN-SH', 'Shanghai', 'cn'),
            ('CN-JS', 'Jiangsu', 'cn'),
            ('CN-ZJ', 'Zhejiang', 'cn'),
            ('CN-AH', 'Anhui', 'cn'),
            ('CN-FJ', 'Fujian', 'cn'),
            ('CN-JX', 'Jiangxi', 'cn'),
            ('CN-SD', 'Shandong', 'cn'),
            ('CN-HA', 'Henan', 'cn'),
            ('CN-HB', 'Hubei', 'cn'),
            ('CN-HN', 'Hunan', 'cn'),
            ('CN-GD', 'Guangdong', 'cn'),
            ('CN-GX', 'Guangxi', 'cn'),
            ('CN-HI', 'Hainan', 'cn'),
            ('CN-CQ', 'Chongqing', 'cn'),
            ('CN-SC', 'Sichuan', 'cn'),
            ('CN-GZ', 'Guizhou', 'cn'),
            ('CN-YN', 'Yunnan', 'cn'),
            ('CN-XZ', 'Tibet', 'cn'),
            ('CN-SA', 'Shaanxi', 'cn'),
            ('CN-GS', 'Gansu', 'cn'),
            ('CN-QH', 'Qinghai', 'cn'),
            ('CN-NX', 'Ningxia', 'cn'),
            ('CN-XJ', 'Xinjiang', 'cn'),
            ('IN-AN', 'Andaman and Nicobar Islands', 'in'),
            ('IN-AP', 'Andhra Pradesh', 'in'),
            ('IN-AR', 'Arunachal Pradesh', 'in'),
            ('IN-AS', 'Assam', 'in'),
            ('IN-BR', 'Bihar', 'in'),
            ('IN-CH', 'Chandigarh', 'in'),
            ('IN-CT', 'Chhattisgarh', 'in'),
            ('IN-DN', 'Dadra and Nagar Haveli and Daman and Diu', 'in'),
            ('IN-DD', 'Daman and Diu', 'in'),
            ('IN-DL', 'Delhi', 'in'),
            ('IN-GA', 'Goa', 'in'),
            ('IN-GJ', 'Gujarat', 'in'),
            ('IN-HR', 'Haryana', 'in'),
            ('IN-HP', 'Himachal Pradesh', 'in'),
            ('IN-JH', 'Jharkhand', 'in'),
            ('IN-KA', 'Karnataka', 'in'),
            ('IN-KL', 'Kerala', 'in'),
            ('IN-LD', 'Lakshadweep', 'in'),
            ('IN-MP', 'Madhya Pradesh', 'in'),
            ('IN-MH', 'Maharashtra', 'in'),
            ('IN-MN', 'Manipur', 'in'),
            ('IN-ML', 'Meghalaya', 'in'),
            ('IN-MZ', 'Mizoram', 'in'),
            ('IN-NL', 'Nagaland', 'in'),
            ('IN-OR', 'Odisha', 'in'),
            ('IN-PY', 'Puducherry', 'in'),
            ('IN-PB', 'Punjab', 'in'),
            ('IN-RJ', 'Rajasthan', 'in'),
            ('IN-SK', 'Sikkim', 'in'),
            ('IN-TN', 'Tamil Nadu', 'in'),
            ('IN-TG', 'Telangana', 'in'),
            ('IN-TR', 'Tripura', 'in'),
            ('IN-UP', 'Uttar Pradesh', 'in'),
            ('IN-UT', 'Uttarakhand', 'in'),
            ('IN-WB', 'West Bengal', 'in'),
            ('AU-NSW', 'New South Wales', 'au'),
            ('AU-VIC', 'Victoria', 'au'),
            ('AU-QLD', 'Queensland', 'au'),
            ('AU-SA', 'South Australia', 'au'),
            ('AU-WA', 'Western Australia', 'au'),
            ('AU-TAS', 'Tasmania', 'au'),
            ('AU-NT', 'Northern Territory', 'au'),
            ('AU-ACT', 'Australian Capital Territory', 'au'),
            ('NZ-N', 'Northland', 'nz'),
            ('NZ-AUK', 'Auckland', 'nz'),
            ('NZ-WKO', 'Waikato', 'nz'),
            ('NZ-BOP', 'Bay of Plenty', 'nz'),
            ('NZ-GIS', 'Gisborne', 'nz'),
            ('NZ-HKB', 'Hawke''s Bay', 'nz'),
            ('NZ-TKI', 'Taranaki', 'nz'),
            ('NZ-MWT', 'Manawatū-Whanganui', 'nz'),
            ('NZ-WGN', 'Wellington', 'nz'),
            ('NZ-TAS', 'Tasman', 'nz'),
            ('NZ-NEL', 'Nelson', 'nz'),
            ('NZ-MBH', 'Marlborough', 'nz'),
            ('NZ-WTC', 'West Coast', 'nz'),
            ('NZ-CAN', 'Canterbury', 'nz'),
            ('NZ-OTA', 'Otago', 'nz'),
            ('NZ-STL', 'Southland', 'nz'),
            ('ZA-EC', 'Eastern Cape', 'za'),
            ('ZA-FS', 'Free State', 'za'),
            ('ZA-GP', 'Gauteng', 'za'),
            ('ZA-KZN', 'KwaZulu-Natal', 'za'),
            ('ZA-LP', 'Limpopo', 'za'),
            ('ZA-MP', 'Mpumalanga', 'za'),
            ('ZA-NW', 'North West', 'za'),
            ('ZA-NC', 'Northern Cape', 'za'),
            ('ZA-WC', 'Western Cape', 'za'),
            ('EG-ALX', 'Alexandria', 'eg'),
            ('EG-ASN', 'Aswan', 'eg'),
            ('EG-ASY', 'Asyut', 'eg'),
            ('EG-BHR', 'Beheira', 'eg'),
            ('EG-BNS', 'Beni Suef', 'eg'),
            ('EG-C', 'Cairo', 'eg'),
            ('EG-DK', 'Dakahlia', 'eg'),
            ('EG-DAM', 'Damietta', 'eg'),
            ('EG-FYM', 'Faiyum', 'eg'),
            ('EG-GH', 'Gharbia', 'eg'),
            ('EG-GZ', 'Giza', 'eg'),
            ('EG-IS', 'Ismailia', 'eg'),
            ('EG-KB', 'Kafr El Sheikh', 'eg'),
            ('EG-LX', 'Luxor', 'eg'),
            ('EG-MN', 'Minya', 'eg'),
            ('EG-MT', 'Matrouh', 'eg'),
            ('EG-QH', 'Qalyubia', 'eg'),
            ('EG-KFS', 'Qena', 'eg'),
            ('EG-SHG', 'Sohag', 'eg'),
            ('EG-SHR', 'Sharqia', 'eg'),
            ('EG-SIN', 'South Sinai', 'eg'),
            ('EG-SW', 'Suez', 'eg'),
            ('EG-WAD', 'New Valley', 'eg'),
            ('EG-ASD', 'North Sinai', 'eg'),
            ('EG-PTS', 'Port Said', 'eg'),
            ('EG-SKB', 'Suez', 'eg'),
            ('EG-ESI', 'Ismailia', 'eg'),
            ('BR-AC', 'Acre', 'br'),
            ('BR-AL', 'Alagoas', 'br'),
            ('BR-AP', 'Amapá', 'br'),
            ('BR-AM', 'Amazonas', 'br'),
            ('BR-BA', 'Bahia', 'br'),
            ('BR-CE', 'Ceará', 'br'),
            ('BR-DF', 'Federal District', 'br'),
            ('BR-ES', 'Espírito Santo', 'br'),
            ('BR-GO', 'Goiás', 'br'),
            ('BR-MA', 'Maranhão', 'br'),
            ('BR-MT', 'Mato Grosso', 'br'),
            ('BR-MS', 'Mato Grosso do Sul', 'br'),
            ('BR-MG', 'Minas Gerais', 'br'),
            ('BR-PA', 'Pará', 'br'),
            ('BR-PB', 'Paraíba', 'br'),
            ('BR-PR', 'Paraná', 'br'),
            ('BR-PE', 'Pernambuco', 'br'),
            ('BR-PI', 'Piauí', 'br'),
            ('BR-RJ', 'Rio de Janeiro', 'br'),
            ('BR-RN', 'Rio Grande do Norte', 'br'),
            ('BR-RS', 'Rio Grande do Sul', 'br'),
            ('BR-RO', 'Rondônia', 'br'),
            ('BR-RR', 'Roraima', 'br'),
            ('BR-SC', 'Santa Catarina', 'br'),
            ('BR-SP', 'São Paulo', 'br'),
            ('BR-SE', 'Sergipe', 'br'),
            ('BR-TO', 'Tocantins', 'br'),
            ('SE-AB', 'Stockholm', 'se'),
            ('SE-AC', 'Västerbotten', 'se'),
            ('SE-BD', 'Norrbotten', 'se'),
            ('SE-C', 'Uppsala', 'se'),
            ('SE-D', 'Södermanland', 'se'),
            ('SE-E', 'Östergötland', 'se'),
            ('SE-F', 'Jönköping', 'se'),
            ('SE-G', 'Kronoberg', 'se'),
            ('SE-H', 'Kalmar', 'se'),
            ('SE-I', 'Gotland', 'se'),
            ('SE-K', 'Blekinge', 'se'),
            ('SE-M', 'Skåne', 'se'),
            ('SE-N', 'Halland', 'se'),
            ('SE-O', 'Västra Götaland', 'se'),
            ('SE-S', 'Värmland', 'se'),
            ('SE-T', 'Örebro', 'se'),
            ('SE-U', 'Västmanland', 'se'),
            ('SE-W', 'Dalarna', 'se'),
            ('SE-X', 'Gävleborg', 'se'),
            ('SE-Y', 'Västernorrland', 'se'),
            ('SE-Z', 'Jämtland', 'se'),
            ('IE-C', 'Connacht', 'ie'),
            ('IE-L', 'Leinster', 'ie'),
            ('IE-M', 'Munster', 'ie'),
            ('IE-U', 'Ulster', 'ie'),
            ('ES-AN', 'Andalucía', 'es'),
            ('ES-AR', 'Aragón', 'es'),
            ('ES-AS', 'Asturias', 'es'),
            ('ES-CB', 'Cantabria', 'es'),
            ('ES-CL', 'Castilla y León', 'es'),
            ('ES-CM', 'Castilla-La Mancha', 'es'),
            ('ES-CN', 'Canarias', 'es'),
            ('ES-CT', 'Cataluña', 'es'),
            ('ES-EX', 'Extremadura', 'es'),
            ('ES-GA', 'Galicia', 'es'),
            ('ES-IB', 'Islas Baleares', 'es'),
            ('ES-MD', 'Madrid', 'es'),
            ('ES-MC', 'Murcia', 'es'),
            ('ES-NC', 'Navarra', 'es'),
            ('ES-PV', 'País Vasco', 'es'),
            ('ES-RI', 'La Rioja', 'es'),
            ('ES-VC', 'Comunidad Valenciana', 'es'),
            ('CH-AG', 'Aargau', 'ch'),
            ('CH-AR', 'Appenzell Ausserrhoden', 'ch'),
            ('CH-AI', 'Appenzell Innerrhoden', 'ch'),
            ('CH-BL', 'Basel-Landschaft', 'ch'),
            ('CH-BS', 'Basel-Stadt', 'ch'),
            ('CH-BE', 'Bern', 'ch'),
            ('CH-FR', 'Fribourg', 'ch'),
            ('CH-GE', 'Genève', 'ch'),
            ('CH-GL', 'Glarus', 'ch'),
            ('CH-GR', 'Graubünden', 'ch'),
            ('CH-JU', 'Jura', 'ch'),
            ('CH-LU', 'Luzern', 'ch'),
            ('CH-NE', 'Neuchâtel', 'ch'),
            ('CH-NW', 'Nidwalden', 'ch'),
            ('CH-OW', 'Obwalden', 'ch'),
            ('CH-SH', 'Schaffhausen', 'ch'),
            ('CH-SZ', 'Schwyz', 'ch'),
            ('CH-SO', 'Solothurn', 'ch'),
            ('CH-SG', 'St. Gallen', 'ch'),
            ('CH-TG', 'Thurgau', 'ch'),
            ('CH-TI', 'Ticino', 'ch'),
            ('CH-UR', 'Uri', 'ch'),
            ('CH-VS', 'Valais', 'ch'),
            ('CH-VD', 'Vaud', 'ch'),
            ('CH-ZG', 'Zug', 'ch'),
            ('CH-ZH', 'Zürich', 'ch'),
            ('IT-65', 'Abruzzo', 'it'),
            ('IT-77', 'Basilicata', 'it'),
            ('IT-78', 'Calabria', 'it'),
            ('IT-72', 'Campania', 'it'),
            ('IT-45', 'Emilia-Romagna', 'it'),
            ('IT-36', 'Friuli Venezia Giulia', 'it'),
            ('IT-62', 'Lazio', 'it'),
            ('IT-42', 'Liguria', 'it'),
            ('IT-25', 'Lombardia', 'it'),
            ('IT-57', 'Marche', 'it'),
            ('IT-67', 'Molise', 'it'),
            ('IT-21', 'Piemonte', 'it'),
            ('IT-75', 'Puglia', 'it'),
            ('IT-88', 'Sardegna', 'it'),
            ('IT-82', 'Sicilia', 'it'),
            ('IT-52', 'Toscana', 'it'),
            ('IT-32', 'Trentino-Alto Adige', 'it'),
            ('IT-55', 'Umbria', 'it'),
            ('IT-23', 'Valle d''Aosta', 'it'),
            ('IT-34', 'Veneto', 'it'),
            ('IS-1', 'Höfuðborgarsvæði', 'is'),
            ('IS-2', 'Suðurnes', 'is'),
            ('IS-3', 'Vesturland', 'is'),
            ('IS-4', 'Vestfirðir', 'is'),
            ('IS-5', 'Norðurland vestra', 'is'),
            ('IS-6', 'Norðurland eystra', 'is'),
            ('IS-7', 'Austurland', 'is'),
            ('IS-8', 'Suðurland', 'is'),
        ]

        
        if not force and (Country.objects.exists() or Region.objects.exists()):
            self.stdout.write(self.style.WARNING(
                'Countries or regions already exist in the database. Use --force to override.'
            ))
            return

        try:
            with transaction.atomic():
                if force:
                    self.sync_countries(countries)
                    self.sync_regions(regions)
                else:
                    self.insert_countries(countries)
                    self.insert_regions(regions)
                
                self.stdout.write(self.style.SUCCESS('Successfully imported world travel data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {str(e)}'))

    def sync_countries(self, countries):
        country_codes = [code for _, code, _ in countries]
        Country.objects.exclude(country_code__in=country_codes).delete()
        
        for name, country_code, continent in countries:
            country, created = Country.objects.update_or_create(
                country_code=country_code,
                defaults={'name': name, 'continent': continent}
            )
            if created:
                saveCountryFlag(country_code)
                self.stdout.write(f'Inserted {name} into worldtravel countries')
            else:
                saveCountryFlag(country_code)
                self.stdout.write(f'Updated {name} in worldtravel countries')

    def sync_regions(self, regions):
        region_ids = [id for id, _, _ in regions]
        Region.objects.exclude(id__in=region_ids).delete()

        for id, name, country_code in regions:
            country = Country.objects.get(country_code=country_code)
            region, created = Region.objects.update_or_create(
                id=id,
                defaults={'name': name, 'country': country}
            )
            if created:
                self.stdout.write(f'Inserted {name} into worldtravel regions')
            else:
                self.stdout.write(f'Updated {name} in worldtravel regions')

    def insert_countries(self, countries):
        for name, country_code, continent in countries:
            country, created = Country.objects.get_or_create(
                country_code=country_code,
                defaults={'name': name, 'continent': continent}
            )
            if created:
                saveCountryFlag(country_code)
                self.stdout.write(f'Inserted {name} into worldtravel countries')
            else:
                saveCountryFlag(country_code)
                self.stdout.write(f'{name} already exists in worldtravel countries')

    def insert_regions(self, regions):
        for id, name, country_code in regions:
            country = Country.objects.get(country_code=country_code)
            region, created = Region.objects.get_or_create(
                id=id,
                defaults={'name': name, 'country': country}
            )
            if created:
                self.stdout.write(f'Inserted {name} into worldtravel regions')
            else:
                self.stdout.write(f'{name} already exists in worldtravel regions')