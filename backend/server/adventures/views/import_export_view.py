# views.py
import json
import zipfile
import tempfile
import os
from datetime import datetime
from django.http import HttpResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from adventures.models import (
    Location, Collection, Transportation, Note, Checklist, ChecklistItem,
    LocationImage, Attachment, Category, Lodging, Visit
)
from worldtravel.models import VisitedCity, VisitedRegion, City, Region, Country

User = get_user_model()

class BackupViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    """
    Simple ViewSet for handling backup and import operations
    """
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export all user data as a ZIP file containing JSON data and files
        """
        user = request.user
        
        # Build export data structure
        export_data = {
            'version': settings.ADVENTURELOG_RELEASE_VERSION,
            'export_date': datetime.now().isoformat(),
            'user_email': user.email,
            'user_username': user.username,
            'categories': [],
            'collections': [],
            'locations': [],
            'transportation': [],
            'notes': [],
            'checklists': [],
            'lodging': [],
            'visited_cities': [],
            'visited_regions': []
        }

        # Export Visited Cities
        for visited_city in user.visitedcity_set.all():
            export_data['visited_cities'].append({
                'city': visited_city.city.id,
            })

        # Export Visited Regions
        for visited_region in user.visitedregion_set.all():
            export_data['visited_regions'].append({
                'region': visited_region.region.id,
            })
        
        # Export Categories
        for category in user.category_set.all():
            export_data['categories'].append({
                'name': category.name,
                'display_name': category.display_name,
                'icon': category.icon,
            })
        
        # Export Collections
        for idx, collection in enumerate(user.collection_set.all()):
            export_data['collections'].append({
                'export_id': idx,  # Add unique identifier for this export
                'name': collection.name,
                'description': collection.description,
                'is_public': collection.is_public,
                'start_date': collection.start_date.isoformat() if collection.start_date else None,
                'end_date': collection.end_date.isoformat() if collection.end_date else None,
                'is_archived': collection.is_archived,
                'link': collection.link,
                'shared_with_user_ids': [str(uuid) for uuid in collection.shared_with.values_list('uuid', flat=True)]
            })
        
        # Create collection name to export_id mapping
        collection_name_to_id = {col.name: idx for idx, col in enumerate(user.collection_set.all())}
        
        # Export locations with related data
        for idx, location in enumerate(user.location_set.all()):
            location_data = {
                'export_id': idx,  # Add unique identifier for this export
                'name': location.name,
                'location': location.location,
                'tags': location.tags,
                'description': location.description,
                'rating': location.rating,
                'link': location.link,
                'is_public': location.is_public,
                'longitude': str(location.longitude) if location.longitude else None,
                'latitude': str(location.latitude) if location.latitude else None,
                'city': location.city_id,
                'region': location.region_id,
                'country': location.country_id,
                'category_name': location.category.name if location.category else None,
                'collection_export_ids': [collection_name_to_id[col_name] for col_name in location.collections.values_list('name', flat=True) if col_name in collection_name_to_id],
                'visits': [],
                'images': [],
                'attachments': []
            }
            
            # Add visits
            for visit in location.visits.all():
                location_data['visits'].append({
                    'start_date': visit.start_date.isoformat() if visit.start_date else None,
                    'end_date': visit.end_date.isoformat() if visit.end_date else None,
                    'timezone': visit.timezone,
                    'notes': visit.notes
                })
            
            # Add images
            for image in location.images.all():
                image_data = {
                    'immich_id': image.immich_id,
                    'is_primary': image.is_primary,
                    'filename': None
                }
                if image.image:
                    image_data['filename'] = image.image.name.split('/')[-1]
                location_data['images'].append(image_data)
            
            # Add attachments
            for attachment in location.attachments.all():
                attachment_data = {
                    'name': attachment.name,
                    'filename': None
                }
                if attachment.file:
                    attachment_data['filename'] = attachment.file.name.split('/')[-1]
                location_data['attachments'].append(attachment_data)
            
            export_data['locations'].append(location_data)
        
        # Export Transportation
        for transport in user.transportation_set.all():
            collection_export_id = None
            if transport.collection:
                collection_export_id = collection_name_to_id.get(transport.collection.name)
            
            export_data['transportation'].append({
                'type': transport.type,
                'name': transport.name,
                'description': transport.description,
                'rating': transport.rating,
                'link': transport.link,
                'date': transport.date.isoformat() if transport.date else None,
                'end_date': transport.end_date.isoformat() if transport.end_date else None,
                'start_timezone': transport.start_timezone,
                'end_timezone': transport.end_timezone,
                'flight_number': transport.flight_number,
                'from_location': transport.from_location,
                'origin_latitude': str(transport.origin_latitude) if transport.origin_latitude else None,
                'origin_longitude': str(transport.origin_longitude) if transport.origin_longitude else None,
                'destination_latitude': str(transport.destination_latitude) if transport.destination_latitude else None,
                'destination_longitude': str(transport.destination_longitude) if transport.destination_longitude else None,
                'to_location': transport.to_location,
                'is_public': transport.is_public,
                'collection_export_id': collection_export_id
            })
        
        # Export Notes
        for note in user.note_set.all():
            collection_export_id = None
            if note.collection:
                collection_export_id = collection_name_to_id.get(note.collection.name)
                
            export_data['notes'].append({
                'name': note.name,
                'content': note.content,
                'links': note.links,
                'date': note.date.isoformat() if note.date else None,
                'is_public': note.is_public,
                'collection_export_id': collection_export_id
            })
        
        # Export Checklists
        for checklist in user.checklist_set.all():
            collection_export_id = None
            if checklist.collection:
                collection_export_id = collection_name_to_id.get(checklist.collection.name)
                
            checklist_data = {
                'name': checklist.name,
                'date': checklist.date.isoformat() if checklist.date else None,
                'is_public': checklist.is_public,
                'collection_export_id': collection_export_id,
                'items': []
            }
            
            # Add checklist items
            for item in checklist.checklistitem_set.all():
                checklist_data['items'].append({
                    'name': item.name,
                    'is_checked': item.is_checked
                })
            
            export_data['checklists'].append(checklist_data)
        
        # Export Lodging
        for lodging in user.lodging_set.all():
            collection_export_id = None
            if lodging.collection:
                collection_export_id = collection_name_to_id.get(lodging.collection.name)
                
            export_data['lodging'].append({
                'name': lodging.name,
                'type': lodging.type,
                'description': lodging.description,
                'rating': lodging.rating,
                'link': lodging.link,
                'check_in': lodging.check_in.isoformat() if lodging.check_in else None,
                'check_out': lodging.check_out.isoformat() if lodging.check_out else None,
                'timezone': lodging.timezone,
                'reservation_number': lodging.reservation_number,
                'price': str(lodging.price) if lodging.price else None,
                'latitude': str(lodging.latitude) if lodging.latitude else None,
                'longitude': str(lodging.longitude) if lodging.longitude else None,
                'location': lodging.location,
                'is_public': lodging.is_public,
                'collection_export_id': collection_export_id
            })
        
        # Create ZIP file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add JSON data
                zip_file.writestr('data.json', json.dumps(export_data, indent=2))
                
                # Add images and attachments
                files_added = set()
                
                for location in user.location_set.all():
                    # Add images
                    for image in location.images.all():
                        if image.image and image.image.name not in files_added:
                            try:
                                image_content = default_storage.open(image.image.name).read()
                                filename = image.image.name.split('/')[-1]
                                zip_file.writestr(f'images/{filename}', image_content)
                                files_added.add(image.image.name)
                            except Exception as e:
                                print(f"Error adding image {image.image.name}: {e}")
                    
                    # Add attachments
                    for attachment in location.attachments.all():
                        if attachment.file and attachment.file.name not in files_added:
                            try:
                                file_content = default_storage.open(attachment.file.name).read()
                                filename = attachment.file.name.split('/')[-1]
                                zip_file.writestr(f'attachments/{filename}', file_content)
                                files_added.add(attachment.file.name)
                            except Exception as e:
                                print(f"Error adding attachment {attachment.file.name}: {e}")
        
        # Return ZIP file as response
        with open(tmp_file.name, 'rb') as zip_file:
            response = HttpResponse(zip_file.read(), content_type='application/zip')
            filename = f"adventurelog_backup_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Clean up
        os.unlink(tmp_file.name)
        return response
    
    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser],
        url_path='import',  # changes the URL path to /import
        url_name='import'   # changes the reverse name to 'import'
    )
    def import_data(self, request):
        """
        Import data from a ZIP backup file
        """
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if 'confirm' not in request.data or request.data['confirm'] != 'yes':
            return Response({'error': 'Confirmation required to proceed with import'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        backup_file = request.FILES['file']
        user = request.user
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            for chunk in backup_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            with zipfile.ZipFile(tmp_file_path, 'r') as zip_file:
                # Validate backup structure
                if 'data.json' not in zip_file.namelist():
                    return Response({'error': 'Invalid backup file - missing data.json'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                # Load data
                backup_data = json.loads(zip_file.read('data.json').decode('utf-8'))
                
                # Import with transaction
                with transaction.atomic():
                    # Clear existing data first
                    self._clear_user_data(user)
                    summary = self._import_data(backup_data, zip_file, user)
                
                return Response({
                    'success': True,
                    'message': 'Data imported successfully',
                    'summary': summary
                }, status=status.HTTP_200_OK)
                
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON in backup file'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            import logging
            logging.error("Import failed", exc_info=True)
            return Response({'error': 'An internal error occurred during import'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        finally:
            os.unlink(tmp_file_path)
    
    def _clear_user_data(self, user):
        """Clear all existing user data before import"""
        # Delete in reverse order of dependencies
        user.checklistitem_set.all().delete()
        user.checklist_set.all().delete()
        user.note_set.all().delete()
        user.transportation_set.all().delete()
        user.lodging_set.all().delete()
        
        # Delete location-related data
        user.locationimage_set.all().delete()
        user.attachment_set.all().delete()
        # Visits are deleted via cascade when locations are deleted
        user.location_set.all().delete()
        
        # Delete collections and categories last
        user.collection_set.all().delete()
        user.category_set.all().delete()

        # Clear visited cities and regions
        user.visitedcity_set.all().delete()
        user.visitedregion_set.all().delete()
    
    def _import_data(self, backup_data, zip_file, user):
        """Import backup data and return summary"""
        # Track mappings and counts
        category_map = {}
        collection_map = {}  # Map export_id to actual collection object
        summary = {
            'categories': 0, 'collections': 0, 'locations': 0,
            'transportation': 0, 'notes': 0, 'checklists': 0,
            'checklist_items': 0, 'lodging': 0, 'images': 0, 'attachments': 0, 'visited_cities': 0, 'visited_regions': 0
        }

        # Import Visited Cities
        for city_data in backup_data.get('visited_cities', []):
            try:
                city_obj = City.objects.get(id=city_data['city'])
                VisitedCity.objects.create(user=user, city=city_obj)
                summary['visited_cities'] += 1
            except City.DoesNotExist:
                # If city does not exist, we can skip or log it
                pass

        # Import Visited Regions
        for region_data in backup_data.get('visited_regions', []):
            try:
                region_obj = Region.objects.get(id=region_data['region'])
                VisitedRegion.objects.create(user=user, region=region_obj)
                summary['visited_regions'] += 1
            except Region.DoesNotExist:
                # If region does not exist, we can skip or log it
                pass
        
        # Import Categories
        for cat_data in backup_data.get('categories', []):
            category = Category.objects.create(
                user=user,
                name=cat_data['name'],
                display_name=cat_data['display_name'],
                icon=cat_data.get('icon', '🌍')
            )
            category_map[cat_data['name']] = category
            summary['categories'] += 1
        
        # Import Collections
        for col_data in backup_data.get('collections', []):
            collection = Collection.objects.create(
                user=user,
                name=col_data['name'],
                description=col_data.get('description', ''),
                is_public=col_data.get('is_public', False),
                start_date=col_data.get('start_date'),
                end_date=col_data.get('end_date'),
                is_archived=col_data.get('is_archived', False),
                link=col_data.get('link')
            )
            collection_map[col_data['export_id']] = collection
            summary['collections'] += 1
            
            # Handle shared users
            for uuid in col_data.get('shared_with_user_ids', []):
                try:
                    shared_user = User.objects.get(uuid=uuid)
                    if shared_user.public_profile:
                        collection.shared_with.add(shared_user)
                except User.DoesNotExist:
                    pass
        
        # Import Locations
        for adv_data in backup_data.get('locations', []):

            city = None
            if adv_data.get('city'):
                try:
                    city = City.objects.get(id=adv_data['city'])
                except City.DoesNotExist:
                    city = None

            region = None
            if adv_data.get('region'):
                try:
                    region = Region.objects.get(id=adv_data['region'])
                except Region.DoesNotExist:
                    region = None

            country = None
            if adv_data.get('country'):
                try:
                    country = Country.objects.get(id=adv_data['country'])
                except Country.DoesNotExist:
                    country = None

            location = Location(
                user=user,
                name=adv_data['name'],
                location=adv_data.get('location'),
                tags=adv_data.get('tags', []),
                description=adv_data.get('description'),
                rating=adv_data.get('rating'),
                link=adv_data.get('link'),
                is_public=adv_data.get('is_public', False),
                longitude=adv_data.get('longitude'),
                latitude=adv_data.get('latitude'),
                city=city,
                region=region,
                country=country,
                category=category_map.get(adv_data.get('category_name'))
            )
            location.save(_skip_geocode=True)  # Skip geocoding for now
            
            # Add to collections using export_ids
            for collection_export_id in adv_data.get('collection_export_ids', []):
                if collection_export_id in collection_map:
                    location.collections.add(collection_map[collection_export_id])
            
            # Import visits
            for visit_data in adv_data.get('visits', []):
                Visit.objects.create(
                    location=location,
                    start_date=visit_data.get('start_date'),
                    end_date=visit_data.get('end_date'),
                    timezone=visit_data.get('timezone'),
                    notes=visit_data.get('notes')
                )
            
            # Import images
            for img_data in adv_data.get('images', []):
                immich_id = img_data.get('immich_id')
                if immich_id:
                    LocationImage.objects.create(
                        user=user,
                        location=location,
                        immich_id=immich_id,
                        is_primary=img_data.get('is_primary', False)
                    )
                    summary['images'] += 1
                else:
                    filename = img_data.get('filename')
                    if filename:
                        try:
                            img_content = zip_file.read(f'images/{filename}')
                            img_file = ContentFile(img_content, name=filename)
                            LocationImage.objects.create(
                                user=user,
                                location=location,
                                image=img_file,
                                is_primary=img_data.get('is_primary', False)
                            )
                            summary['images'] += 1
                        except KeyError:
                            pass
            
            # Import attachments
            for att_data in adv_data.get('attachments', []):
                filename = att_data.get('filename')
                if filename:
                    try:
                        att_content = zip_file.read(f'attachments/{filename}')
                        att_file = ContentFile(att_content, name=filename)
                        Attachment.objects.create(
                            user=user,
                            location=location,
                            file=att_file,
                            name=att_data.get('name')
                        )
                        summary['attachments'] += 1
                    except KeyError:
                        pass
            
            summary['locations'] += 1
        
        # Import Transportation
        for trans_data in backup_data.get('transportation', []):
            collection = None
            if trans_data.get('collection_export_id') is not None:
                collection = collection_map.get(trans_data['collection_export_id'])
                
            Transportation.objects.create(
                user=user,
                type=trans_data['type'],
                name=trans_data['name'],
                description=trans_data.get('description'),
                rating=trans_data.get('rating'),
                link=trans_data.get('link'),
                date=trans_data.get('date'),
                end_date=trans_data.get('end_date'),
                start_timezone=trans_data.get('start_timezone'),
                end_timezone=trans_data.get('end_timezone'),
                flight_number=trans_data.get('flight_number'),
                from_location=trans_data.get('from_location'),
                origin_latitude=trans_data.get('origin_latitude'),
                origin_longitude=trans_data.get('origin_longitude'),
                destination_latitude=trans_data.get('destination_latitude'),
                destination_longitude=trans_data.get('destination_longitude'),
                to_location=trans_data.get('to_location'),
                is_public=trans_data.get('is_public', False),
                collection=collection
            )
            summary['transportation'] += 1
        
        # Import Notes
        for note_data in backup_data.get('notes', []):
            collection = None
            if note_data.get('collection_export_id') is not None:
                collection = collection_map.get(note_data['collection_export_id'])
                
            Note.objects.create(
                user=user,
                name=note_data['name'],
                content=note_data.get('content'),
                links=note_data.get('links', []),
                date=note_data.get('date'),
                is_public=note_data.get('is_public', False),
                collection=collection
            )
            summary['notes'] += 1
        
        # Import Checklists
        for check_data in backup_data.get('checklists', []):
            collection = None
            if check_data.get('collection_export_id') is not None:
                collection = collection_map.get(check_data['collection_export_id'])
                
            checklist = Checklist.objects.create(
                user=user,
                name=check_data['name'],
                date=check_data.get('date'),
                is_public=check_data.get('is_public', False),
                collection=collection
            )
            
            # Import checklist items
            for item_data in check_data.get('items', []):
                ChecklistItem.objects.create(
                    user=user,
                    checklist=checklist,
                    name=item_data['name'],
                    is_checked=item_data.get('is_checked', False)
                )
                summary['checklist_items'] += 1
            
            summary['checklists'] += 1
        
        # Import Lodging
        for lodg_data in backup_data.get('lodging', []):
            collection = None
            if lodg_data.get('collection_export_id') is not None:
                collection = collection_map.get(lodg_data['collection_export_id'])
                
            Lodging.objects.create(
                user=user,
                name=lodg_data['name'],
                type=lodg_data.get('type', 'other'),
                description=lodg_data.get('description'),
                rating=lodg_data.get('rating'),
                link=lodg_data.get('link'),
                check_in=lodg_data.get('check_in'),
                check_out=lodg_data.get('check_out'),
                timezone=lodg_data.get('timezone'),
                reservation_number=lodg_data.get('reservation_number'),
                price=lodg_data.get('price'),
                latitude=lodg_data.get('latitude'),
                longitude=lodg_data.get('longitude'),
                location=lodg_data.get('location'),
                is_public=lodg_data.get('is_public', False),
                collection=collection
            )
            summary['lodging'] += 1
        
        return summary