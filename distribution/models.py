import os, requests

from dotenv import load_dotenv



from django.core.mail import send_mail
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.base import ObjectDoesNotExist

from django.utils import timezone
load_dotenv()
COMPANY_KEY = os.environ['QGENDA_COMPANY_KEY']
EMAIL = os.environ['QGENDA_EMAIL']
PASSWORD = os.environ['QGENDA_PASSWORD']



class ProviderManager(models.Manager):
    def get_or_create_from_qgenda_name(self, qgenda_name):
        return self.get_or_create(qgenda_name=qgenda_name)[0]


class Provider(models.Model):
    qgenda_name = models.CharField(max_length=20, null=True, unique=True)
    display_name = models.CharField(max_length=20, unique=True)
    max_total_census = models.SmallIntegerField(default=17, validators=[MinValueValidator(0), MaxValueValidator(30)])
    max_CCU_census = models.SmallIntegerField(default=17, validators=[MinValueValidator(0), MaxValueValidator(30)])
    max_COVID_census = models.SmallIntegerField(default=17, validators=[MinValueValidator(0), MaxValueValidator(30)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.qgenda_name and not self.id:
            self.display_name = self.qgenda_name

    def __str__(self):
        return self.display_name

    def set_max_censuses_to_census_track(self, census_track):
        if census_track == 'default':
            self.max_total_census, self.max_CCU_census, self.max_COVID_census = 17, 17, 17
        elif census_track == 'teaching' or census_track == 'orienting':
            self.max_total_census, self.max_CCU_census, self.max_COVID_census = 12, 12, 12
        elif census_track == 'COVID-free':
            self.max_COVID_census = 0
        self.save()

    objects = ProviderManager()


class RoleManager(models.Manager):
    def get_or_create_from_qgenda_name(self, qgenda_name):
        try:
            unspecified_role = self.get(qgenda_name=qgenda_name)
            try:
                rounder_role = unspecified_role.rounderrole
                return rounder_role
            except ObjectDoesNotExist:
                try:
                    secondary_role = unspecified_role.secondaryrole
                    return secondary_role
                except ObjectDoesNotExist:
                    return unspecified_role
        except ObjectDoesNotExist:
            stripped_name = ''.join(char for char in qgenda_name.upper() if char.isalpha())
            if stripped_name.startswith('DOC'):
                return RounderRole.objects.create(qgenda_name=qgenda_name)
            return SecondaryRole.objects.create(qgenda_name=qgenda_name)


class Role(models.Model):
    qgenda_name = models.CharField(max_length=20, null=True, unique=True)
    display_name = models.CharField(max_length=20, unique=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.qgenda_name:
            self.display_name = self.qgenda_name

    def __str__(self):
        return self.display_name

    objects = RoleManager()


class RounderRole(Role):
    initial_sort_key = models.SmallIntegerField()

    # class Meta:
    #     ordering = ['sort_key']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stripped_letters = ''.join(char for char in self.qgenda_name.upper() if char.isalpha())
        stripped_numbers = ''.join(char for char in self.qgenda_name.upper() if char.isnumeric())
        if stripped_letters.startswith('DOC'):
            self.initial_sort_key = 0
        # elif stripped_letters.startswith('APP'):
        #     self.sort_key = 100
        try:
            self.initial_sort_key += int(stripped_numbers)
        except ValueError:
            pass


class SecondaryRole(Role):
    pass


class QGendaDataSetManager(models.Manager):
    def get_updated_dataset(self, date, update_if_gte_mins=60):
        last_dataset_for_date = self.filter(date=date).last()
        if last_dataset_for_date and \
                timezone.localtime() - last_dataset_for_date.created < timezone.timedelta(minutes=update_if_gte_mins):
            return last_dataset_for_date
        return self.create_new_dataset(date=date)

    def create_new_dataset(self, date):
        new_dataset = QGendaDataSet()
        new_dataset.date = date
        new_dataset.created = timezone.localtime()
        new_dataset.raw_data = self.get_raw_data(date=date)
        new_dataset.relevant_data = self.get_relevant_data(raw_data=new_dataset.raw_data)
        new_dataset.save()
        return new_dataset

    def get_raw_data(self, date):
        token = self.get_authorization_token()
        auth = f"{token.json()['token_type']} {token.json()['access_token']}"
        headers = {'Authorization': auth}
        url = f'https://api.qgenda.com/v2/schedule?companyKey={COMPANY_KEY}&startDate={date.strftime("%m/%d/%Y")}'
        try:
            with requests.get(url=url, headers=headers) as r:
                return r.json()
        except:
            raise Exception('Failed to get schedule from QGenda')

    def get_relevant_data(self, raw_data):
        relevant_data = []
        for line in raw_data:
            if not line['IsStruck']:
                relevant_data.append({'StaffAbbrev': line['StaffAbbrev'], 'TaskName': line['TaskName']})
        return relevant_data

    def get_authorization_token(self):
        try:
            with requests.post(
                    url='https://api.qgenda.com/v2/login',
                    data={
                        'email': EMAIL,
                        'password': PASSWORD
                    }
            ) as r:
                return r
        except:
            raise Exception('Failed to get authorization token from QGenda')


class QGendaDataSet(models.Model):
    date = models.DateField()
    created = models.DateTimeField()
    raw_data = models.TextField()
    relevant_data = models.TextField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.localtime()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"qgenda_dataset_{self.date.strftime('%m/%d/%y')}_{self.created.strftime('%H:%M')}"

    objects = QGendaDataSetManager()


class DistributionManager(models.Manager):
    def get_last_for_date_or_create_new(self, date):
        if prior_distribution := self.filter(date=date).last():  # duplicate last distribution for date if one exists
            return prior_distribution
        else:  # create new distribution if none for self.fail('finish the test!')

            return self.create_new_distribution_from_qgenda_data(date=date)

    def create_new_distribution_from_qgenda_data(self, date):
        # creates distribution from updated dataset:  new dataset if last > 60mins old, existing dataset if self.fail('Finish the test!')
        qgenda_dataset = QGendaDataSet.objects.get_updated_dataset(date=date)
        return self.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=date, relevant_data=qgenda_dataset.relevant_data)

    def create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(self, date, relevant_data):
        distribution = Distribution.objects.create(date=date)
        for dict in relevant_data:
            provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name=dict['StaffAbbrev'])
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                provider=provider, distribution=distribution)
            role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=dict['TaskName'])
            line_item.assign_role(role=role)
        distribution.assign_line_item_batting_order_from_initial_sort_key()
        distribution.create_blank_starting_census_for_each_rounding_line_item()
        return distribution


class Distribution(models.Model):
    date = models.DateField()
    created = models.DateTimeField()
    count_to_distribute = models.SmallIntegerField(null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.localtime()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"distribution_{self.date.strftime('%m/%d/%y')}_{self.created.strftime('%H:%M')}"

    def assign_line_item_batting_order_from_initial_sort_key(self):
        rounder_line_items = self.line_items.filter(rounder_role__isnull=False)
        sorted_rounder_line_items = sorted(rounder_line_items,
                                           key=lambda line_item: line_item.rounder_role.initial_sort_key)
        for index, line_item in enumerate(sorted_rounder_line_items):
            line_item.position_in_batting_order = index + 1
            line_item.save()

    def return_ordered_rounder_line_items(self):
        return self.line_items.filter(rounder_role__isnull=False)

    def move_line_item_to_next_up(self, next_up_line_item):
        line_items = self.return_ordered_rounder_line_items()
        line_item_count = line_items.count()
        next_up_starting_batting_order = next_up_line_item.position_in_batting_order
        for line_item in line_items:
            line_item.position_in_batting_order = \
                ((line_item.position_in_batting_order + line_item_count - next_up_starting_batting_order) \
                 % line_item_count) + 1
            line_item.save()

    def shift_up_in_batting_order(self, rising_line_item):
        current_position = rising_line_item.position_in_batting_order
        if current_position <= 1:
            pass
        else:
            falling_line_item = self.return_ordered_rounder_line_items().get(
                position_in_batting_order=current_position - 1)
            falling_line_item.position_in_batting_order += 1
            falling_line_item.save()
            rising_line_item.position_in_batting_order -= 1
            rising_line_item.save()

    def delete_rounder(self, line_item):
        current_position = line_item.position_in_batting_order
        line_item.delete()
        for line_item in self.return_ordered_rounder_line_items():
            if line_item.position_in_batting_order > current_position:
                line_item.position_in_batting_order -= 1
                line_item.save()

    def return_alphabetical_rounders(self):
        return Provider.objects.filter(line_items__in=self.return_ordered_rounder_line_items()).order_by('display_name')

    def create_blank_starting_census_for_each_rounding_line_item(self):
        rounder_line_items = self.return_ordered_rounder_line_items()
        for rounder_line_item in rounder_line_items:
            StartingCensus.objects.create(distribution_line_item=rounder_line_item)

    def assign_all_seen_patients(self):
        self.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        self.assign_bounceback_patients()
        self.allocate_total_patients()
        # each assign step allocates its type of patients, assigns the patients, then updates the assigned_census
        self.assign_dual_positive_patients()
        self.assign_COVID_positive_patients()
        self.assign_CCU_positive_patients()
        self.assign_dual_negative_patients()

    def assign_not_seen_patients(self):
        self.assign_not_seen_bounceback_patients()
        self.assign_not_seen_non_bounceback_patients()

    def assign_all_patients(self):
        self.assign_all_seen_patients()
        self.assign_not_seen_patients()

    def set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients(
            self):
        for patient in self.patients.all():
            patient.distribution_line_item = None
            patient.save()
        for line_item in self.return_ordered_rounder_line_items():
            try:
                line_item.postbouncecensus.delete()
            except ObjectDoesNotExist:
                pass
            try:
                line_item.allocatedcensus.delete()
            except ObjectDoesNotExist:
                pass
            try:
                line_item.assignedcensus.delete()
            except ObjectDoesNotExist:
                pass
            PostBounceCensus.objects.create(distribution_line_item=line_item,
                                            total_census=line_item.startingcensus.total_census,
                                            CCU_census=line_item.startingcensus.CCU_census,
                                            COVID_census=line_item.startingcensus.COVID_census)
            AllocatedCensus.objects.create(distribution_line_item=line_item,
                                           total_census=line_item.startingcensus.total_census,
                                           CCU_census=line_item.startingcensus.CCU_census,
                                           COVID_census=line_item.startingcensus.COVID_census)
            AssignedCensus.objects.create(distribution_line_item=line_item,
                                          total_census=line_item.startingcensus.total_census,
                                          CCU_census=line_item.startingcensus.CCU_census,
                                          COVID_census=line_item.startingcensus.COVID_census)

    def assign_bounceback_patients(self):
        for patient in self.patients.filter(bounce_to__isnull=False, not_seen=False):
            line_item = self.return_ordered_rounder_line_items().get(provider=patient.bounce_to)
            patient.distribution_line_item = line_item
            patient.save()
            line_item.postbouncecensus.total_census += 1
            line_item.allocatedcensus.total_census += 1
            line_item.assignedcensus.total_census += 1
            if patient.CCU:
                line_item.postbouncecensus.CCU_census += 1
                line_item.allocatedcensus.CCU_census += 1
                line_item.assignedcensus.CCU_census += 1
            if patient.COVID:
                line_item.postbouncecensus.COVID_census += 1
                line_item.allocatedcensus.COVID_census += 1
                line_item.assignedcensus.COVID_census += 1
            line_item.postbouncecensus.save()
            line_item.allocatedcensus.save()
            line_item.assignedcensus.save()

    def allocate_total_patients(self):
        count = self.patients.filter(bounce_to__isnull=True, not_seen=False).count()
        for i in range(count):
            lowest_total_census = 100
            latest_lowest_line_item = None
            for line_item in self.return_ordered_rounder_line_items():
                if line_item.allocatedcensus.total_census <= lowest_total_census and \
                        line_item.allocatedcensus.total_census < line_item.provider.max_total_census:
                    latest_lowest_line_item = line_item
                    lowest_total_census = line_item.allocatedcensus.total_census
            if latest_lowest_line_item:
                latest_lowest_line_item.allocatedcensus.total_census += 1
                latest_lowest_line_item.allocatedcensus.save()

    def return_single_highest_affinity_line_item_and_allocate_dual_pos_patient(self):
        highest_affinity_line_item = None
        lowest_carriage = 2  # WFROCC = weighted fractional representation of COVID and CCU carriage
        for line_item in self.return_ordered_rounder_line_items():
            if line_item.allocatedcensus.total_census - line_item.assignedcensus.total_census > \
                    line_item.allocatedcensus.CCU_census - line_item.assignedcensus.CCU_census and \
                    line_item.allocatedcensus.CCU_census < line_item.provider.max_CCU_census and \
                    line_item.allocatedcensus.COVID_census < line_item.provider.max_COVID_census:
                COVID_rate = line_item.allocatedcensus.COVID_census / line_item.allocatedcensus.total_census
                CCU_rate = line_item.allocatedcensus.CCU_census / line_item.allocatedcensus.total_census
                carriage = COVID_rate ** 2 + CCU_rate ** 2
                if carriage <= lowest_carriage:
                    highest_affinity_line_item = line_item
                    lowest_carriage = carriage
        if highest_affinity_line_item:
            highest_affinity_line_item.allocatedcensus.CCU_census += 1
            highest_affinity_line_item.allocatedcensus.COVID_census += 1
            highest_affinity_line_item.allocatedcensus.save()
        return highest_affinity_line_item

    def return_line_items_for_dual_pos_assignment(self):
        highest_affinity_line_items = []
        for patient in self.patients.filter(bounce_to__isnull=True, COVID=True, CCU=True, not_seen=False):
            highest_affinity_line_item = self.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient()
            if highest_affinity_line_item:
                highest_affinity_line_items.append(highest_affinity_line_item)
        return sorted(highest_affinity_line_items, key=lambda line_item: line_item.position_in_batting_order)

    def assign_dual_positive_patients(self):
        line_items_for_dual_pos_assignment = self.return_line_items_for_dual_pos_assignment()
        for index, patient in enumerate(
                self.patients.filter(bounce_to__isnull=True, COVID=True, CCU=True, not_seen=False)):
            try:
                line_item = self.return_ordered_rounder_line_items().get(id=line_items_for_dual_pos_assignment[index].id)
                patient.distribution_line_item = line_item
                patient.save()
                line_item.assignedcensus.total_census += 1
                line_item.assignedcensus.CCU_census += 1
                line_item.assignedcensus.COVID_census += 1
                line_item.assignedcensus.save()
            except IndexError:
                pass

    def return_lowest_CCU_census_line_item_and_allocate_CCU_pos_patient(self):
        lowest_CCU_census = 100
        latest_lowest_line_item = None
        for line_item in self.return_ordered_rounder_line_items():
            if line_item.allocatedcensus.total_census - line_item.assignedcensus.total_census > \
                    line_item.allocatedcensus.CCU_census - line_item.assignedcensus.CCU_census and \
                    line_item.allocatedcensus.CCU_census <= lowest_CCU_census and \
                    line_item.allocatedcensus.CCU_census < line_item.provider.max_CCU_census:
                latest_lowest_line_item = line_item
                lowest_CCU_census = line_item.allocatedcensus.CCU_census
        if latest_lowest_line_item:
            latest_lowest_line_item.allocatedcensus.CCU_census += 1
            latest_lowest_line_item.allocatedcensus.save()
            return latest_lowest_line_item

    def return_line_items_for_CCU_pos_assignment(self):
        CCU_accepting_line_items = []
        for patient in self.patients.filter(bounce_to__isnull=True, COVID=False, CCU=True, not_seen=False):
            CCU_accepting_line_item = self.return_lowest_CCU_census_line_item_and_allocate_CCU_pos_patient()
            if CCU_accepting_line_item:
                CCU_accepting_line_items.append(CCU_accepting_line_item)
        return sorted(CCU_accepting_line_items, key=lambda line_item: line_item.position_in_batting_order)

    def assign_CCU_positive_patients(self):
        line_items_for_CCU_pos_assignment = self.return_line_items_for_CCU_pos_assignment()
        for index, patient in enumerate(
                self.patients.filter(bounce_to__isnull=True, COVID=False, CCU=True, not_seen=False)):
            try:
                line_item = self.return_ordered_rounder_line_items().get(id=line_items_for_CCU_pos_assignment[index].id)
                patient.distribution_line_item = line_item
                patient.save()
                line_item.assignedcensus.total_census += 1
                line_item.assignedcensus.CCU_census += 1
                line_item.assignedcensus.save()
            except IndexError:
                pass

    def return_lowest_COVID_census_line_item_and_allocate_COVID_pos_patient(self):
        lowest_COVID_census = 100
        latest_lowest_line_item = None
        for line_item in self.return_ordered_rounder_line_items():
            if line_item.allocatedcensus.total_census - line_item.assignedcensus.total_census > \
                    line_item.allocatedcensus.COVID_census - line_item.assignedcensus.COVID_census and \
                    line_item.allocatedcensus.COVID_census <= lowest_COVID_census and \
                    line_item.allocatedcensus.COVID_census < line_item.provider.max_COVID_census:
                latest_lowest_line_item = line_item
                lowest_COVID_census = line_item.allocatedcensus.COVID_census
        if latest_lowest_line_item:
            latest_lowest_line_item.allocatedcensus.COVID_census += 1
            latest_lowest_line_item.allocatedcensus.save()
            return latest_lowest_line_item

    def return_line_items_for_COVID_pos_assignment(self):
        COVID_accepting_line_items = []
        for patient in self.patients.filter(bounce_to__isnull=True, COVID=True, CCU=False, not_seen=False):
            COVID_accepting_line_item = self.return_lowest_COVID_census_line_item_and_allocate_COVID_pos_patient()
            if COVID_accepting_line_item:
                COVID_accepting_line_items.append(COVID_accepting_line_item)
        return sorted(COVID_accepting_line_items, key=lambda line_item: line_item.position_in_batting_order)

    def assign_COVID_positive_patients(self):
        line_items_for_COVID_pos_assignment = self.return_line_items_for_COVID_pos_assignment()
        for index, patient in enumerate(
                self.patients.filter(bounce_to__isnull=True, COVID=True, CCU=False, not_seen=False)):
            try:
                line_item = self.return_ordered_rounder_line_items().get(id=line_items_for_COVID_pos_assignment[index].id)
                patient.distribution_line_item = line_item
                patient.save()
                line_item.assignedcensus.total_census += 1
                line_item.assignedcensus.COVID_census += 1
                line_item.assignedcensus.save()
            except IndexError:
                pass

    def assign_dual_negative_patients(self):
        dual_neg_patients = self.patients.filter(bounce_to__isnull=True, COVID=False, CCU=False, not_seen=False)
        for patient in dual_neg_patients:
            for line_item in self.return_ordered_rounder_line_items():
                if line_item.assignedcensus.total_census < line_item.allocatedcensus.total_census:
                    patient.distribution_line_item = line_item
                    patient.save()
                    line_item.assignedcensus.total_census += 1
                    line_item.assignedcensus.save()
                    break

    def assign_not_seen_bounceback_patients(self):
        for patient in self.patients.filter(bounce_to__isnull=False, not_seen=True):
            line_item = self.return_ordered_rounder_line_items().get(provider=patient.bounce_to)
            patient.distribution_line_item = line_item
            patient.save()

    def assign_not_seen_non_bounceback_patients(self):
        line_item_receiving = None
        for patient in self.patients.filter(bounce_to__isnull=True, not_seen=True).order_by('-CCU', '-COVID',
                                                                                            'number_designation'):
            least_assigned_not_seen_patient_count = 100
            for line_item in self.return_ordered_rounder_line_items():
                if patient.CCU:
                    if line_item.startingcensus.CCU_census + line_item.assigned_patients.filter(CCU=True).count() >= \
                            line_item.provider.max_CCU_census:
                        continue
                if patient.COVID:
                    if line_item.startingcensus.COVID_census + line_item.assigned_patients.filter(COVID=True).count() >= \
                            line_item.provider.max_COVID_census:
                        continue
                if line_item.assigned_patients.filter(not_seen=True).count() < least_assigned_not_seen_patient_count and \
                        line_item.startingcensus.total_census + line_item.assigned_patients.count() < \
                        line_item.provider.max_total_census:
                    line_item_receiving = line_item
                    least_assigned_not_seen_patient_count = line_item.assigned_patients.filter(not_seen=True).count()
            if line_item_receiving:
                patient.distribution_line_item = line_item_receiving
                patient.save()
                line_item_receiving = None

    objects = DistributionManager()


class DistributionLineItemManager(models.Manager):
    def get_or_create_from_distribution_and_provider(self, distribution, provider):
        try:
            return self.get(distribution=distribution, provider=provider)
        except ObjectDoesNotExist:
            return self.create(distribution=distribution, provider=provider)


class DistributionLineItem(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='line_items')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='line_items')
    rounder_role = models.ForeignKey(RounderRole, on_delete=models.CASCADE, null=True, related_name='line_items')
    position_in_batting_order = models.SmallIntegerField(null=True)

    class Meta:
        ordering = ['position_in_batting_order']

    def __str__(self):
        if rounder_role := self.rounder_role:
            string = rounder_role.display_name
        else:
            string = 'non-rounder'
        return string + f' {self.provider}'

    def assign_role(self, role):
        if isinstance(role, RounderRole):
            try:
                line_item_prev_assigned_this_role = self.distribution.line_items.get(rounder_role=role)
                line_item_prev_assigned_this_role.rounder_role = None
                line_item_prev_assigned_this_role.save()
            except ObjectDoesNotExist:
                pass
            self.rounder_role = role
            self.save()
        else:  # role must be secondary_role, and needs to create instance of merge table
            merge_table_instance = SecondaryRoleForLineItem.objects.create(secondary_role=role, line_item=self)

    objects = DistributionLineItemManager()


class SecondaryRoleForLineItem(models.Model):
    # confusing concept, but in order to allow many-to-many from line items to secondary roles, need this merge table
    line_item = models.ForeignKey(DistributionLineItem, on_delete=models.CASCADE,
                                  related_name='secondary_roles_for_line_items')
    secondary_role = models.ForeignKey(SecondaryRole, on_delete=models.CASCADE,
                                       related_name='secondary_roles_for_line_items')


class Census(models.Model):
    total_census = models.PositiveSmallIntegerField()
    CCU_census = models.PositiveSmallIntegerField()
    COVID_census = models.PositiveSmallIntegerField()

    class Meta:
        abstract = True


class StartingCensus(Census):
    distribution_line_item = models.OneToOneField(DistributionLineItem, on_delete=models.CASCADE)
    total_census = models.SmallIntegerField(null=True)
    CCU_census = models.SmallIntegerField(blank=True, null=True)
    COVID_census = models.SmallIntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.distribution_line_item.provider.display_name} starting census - ' + \
               f'{self.total_census}({self.CCU_census})[{self.COVID_census}]'


class PostBounceCensus(Census):
    distribution_line_item = models.OneToOneField(DistributionLineItem, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.distribution_line_item.provider.display_name} post-bounce census - ' + \
               f'{self.total_census}({self.CCU_census})[{self.COVID_census}]'


class AllocatedCensus(Census):
    distribution_line_item = models.OneToOneField(DistributionLineItem, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.distribution_line_item.provider.display_name} target census - ' + \
               f'{self.total_census}({self.CCU_census})[{self.COVID_census}]'


class AssignedCensus(Census):
    distribution_line_item = models.OneToOneField(DistributionLineItem, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.distribution_line_item.provider.display_name} target census - ' + \
               f'{self.total_census}({self.CCU_census})[{self.COVID_census}]'


class Patient(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='patients')
    number_designation = models.SmallIntegerField()
    CCU = models.BooleanField(default=False)
    COVID = models.BooleanField(default=False)
    not_seen = models.BooleanField(default=False)
    bounce_to = models.ForeignKey(Provider, blank=True, null=True, on_delete=models.CASCADE)
    distribution_line_item = models.ForeignKey(DistributionLineItem, blank=True, null=True,
                                               on_delete=models.CASCADE, related_name='assigned_patients')


class DistributionEmail(models.Model):
    distribution = models.ForeignKey(Distribution, null=True, on_delete=models.CASCADE)
    subject = models.CharField(max_length=60)
    from_email = models.EmailField(default='noreply@kalusinator.com')
    html_message = models.TextField()
    recipient_text_field = models.TextField(default='')

    def assemble_pt_assignment_context(self):
        distribution = self.distribution
        line_items = distribution.return_ordered_rounder_line_items()
        patient_assignment_dict = {}
        for line_item in line_items:
            assigned_patient_dict = {}
            seen_bounceback_pts = line_item.assigned_patients.filter(bounce_to__isnull=False, not_seen=False)
            seen_dual_pos_pts = line_item.assigned_patients.filter(bounce_to__isnull=True, COVID=True, CCU=True,
                                                                   not_seen=False)
            seen_ccu_pos_pts = line_item.assigned_patients.filter(bounce_to__isnull=True, COVID=False, CCU=True,
                                                                  not_seen=False)
            seen_covid_pos_pts = line_item.assigned_patients.filter(bounce_to__isnull=True, COVID=True, CCU=False,
                                                                    not_seen=False)
            seen_dual_neg_pts = line_item.assigned_patients.filter(bounce_to__isnull=True, COVID=False, CCU=False,
                                                                   not_seen=False)
            not_seen_pts = line_item.assigned_patients.filter(not_seen=True).order_by('-bounce_to', '-CCU', '-COVID')
            assigned_patient_dict.update(
                {'seen_bounceback_pts': seen_bounceback_pts, 'seen_dual_pos_pts': seen_dual_pos_pts,
                 'seen_ccu_pos_pts': seen_ccu_pos_pts,
                 'seen_covid_pos_pts': seen_covid_pos_pts, 'seen_dual_neg_pts': seen_dual_neg_pts,
                 'not_seen_pts': not_seen_pts})
            patient_assignment_dict.update(
                {line_item: assigned_patient_dict})
        unassigned_patient_dict = {}
        seen_bounceback_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                                     not_seen=False).filter(
            bounce_to__isnull=False)
        seen_dual_pos_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                                   not_seen=False).filter(
            bounce_to__isnull=True,
            COVID=True, CCU=True)
        seen_ccu_pos_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                                  not_seen=False).filter(
            bounce_to__isnull=True,
            COVID=False, CCU=True)
        seen_covid_pos_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                                    not_seen=False).filter(
            bounce_to__isnull=True,
            COVID=True, CCU=False)
        seen_dual_neg_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                                   not_seen=False).filter(
            bounce_to__isnull=True,
            COVID=False, CCU=False)
        not_seen_pts = Patient.objects.filter(distribution=distribution, distribution_line_item__isnull=True,
                                              not_seen=True).order_by('-bounce_to', '-CCU', '-COVID')
        unassigned_seen_total_census = Patient.objects.filter(distribution=distribution,
                                                              distribution_line_item__isnull=True,
                                                              not_seen=False).count()
        unassigned_seen_CCU_census = Patient.objects.filter(distribution=distribution,
                                                            distribution_line_item__isnull=True, not_seen=False).filter(
            CCU=True).count()
        unassigned_seen_COVID_census = Patient.objects.filter(distribution=distribution,
                                                              distribution_line_item__isnull=True,
                                                              not_seen=False).filter(
            COVID=True).count()
        unassigned_patient_dict.update(
            {'seen_bounceback_pts': seen_bounceback_pts, 'seen_dual_pos_pts': seen_dual_pos_pts,
             'seen_ccu_pos_pts': seen_ccu_pos_pts,
             'seen_covid_pos_pts': seen_covid_pos_pts, 'seen_dual_neg_pts': seen_dual_neg_pts,
             'not_seen_pts': not_seen_pts,
             'unassigned_seen_total_census': unassigned_seen_total_census,
             'unassigned_seen_CCU_census': unassigned_seen_CCU_census,
             'unassigned_seen_COVID_census': unassigned_seen_COVID_census})
        return {'date': self.distribution.date, 'ordered_line_items': line_items,
                'patient_assignment_dict': patient_assignment_dict, 'unassigned_patient_dict': unassigned_patient_dict}

    def send_distribution_email(self):
        send_mail(subject=self.subject, from_email=self.from_email,
                  recipient_list=[recipient for recipient in self.recipient_text_field], message=self.html_message,
                  html_message=self.html_message)


class EmailAddressee(models.Model):
    displayed_name = models.CharField(max_length=40, null=True, blank=True)
    email_address = models.EmailField()
    visible = models.BooleanField(default=True)
    pre_checked = models.BooleanField(default=False)

    def __str__(self):
        return self.displayed_name


class DistributionEmailRecipients(models.Model):
    distribution_email = models.ForeignKey(DistributionEmail, models.CASCADE)
    email_addressee = models.ForeignKey(EmailAddressee, models.CASCADE)
