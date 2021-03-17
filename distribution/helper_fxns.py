from django.utils import timezone
from .models import Distribution, Provider, DistributionLineItem, RounderRole, Role, StartingCensus, AllocatedCensus, \
    AssignedCensus, PostBounceCensus


def helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items():
    distribution = Distribution.objects.create(date=timezone.localdate())
    qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
    totals = [10, 11, 13, 11]
    CCUs = [2, 3, 2, 1]
    COVIDs = [0, 3, 1, 2]
    orders = [3, 1, 2, 4]
    for i in range(6):
        provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        if i in range(4):
            line_item.position_in_batting_order = orders[i]
            role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i}')
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=totals[i], CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        else:
            role=Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'RISK{i}')
        line_item.assign_role(role=role)
        # if i in range(4):
        #     rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i}')
        #     line_item.rounder_role = rounder_role
        #     line_item.position_in_batting_order = orders[i]
        # else:
        #     role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'RISK{i}')
        #     line_item.



def helper_fxn_add_4_non_rounder_line_items_to_distribution(distribution):
    qgenda_names = ['provE', 'provF', 'provG', 'provH']
    role_names = ['RISK1', 'RISK2', 'PTO/Vacation1', 'PTO/Vacation2']
    for i in range(4):
        provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=role_names[i])
        line_item.assign_role(role=role)
        line_item.save()


