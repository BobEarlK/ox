import mock
from django.core import mail
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from ..helper_fxns import helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items
from ..mock_qgenda_data import mock_qgenda_relevant_data
from ..models import Distribution, QGendaDataSet, Provider, Role, RounderRole, SecondaryRole, DistributionLineItem, \
    StartingCensus, PostBounceCensus, Patient, DistributionEmail, DistributionEmailRecipients, EmailAddressee


class ProviderTests(TestCase):
    def test_can_create_provider_from_qgenda_name(self):
        self.assertEqual(Provider.objects.count(), 0)
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        self.assertEqual(Provider.objects.count(), 1)
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvB')
        self.assertEqual(Provider.objects.count(), 2)

    def test_get_or_create_from_qgenda_name_returns_existing_provider_if_provider_already_created(self):
        self.assertEqual(Provider.objects.count(), 0)
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        self.assertEqual(Provider.objects.count(), 1)
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        self.assertEqual(Provider.objects.count(), 1)

    def test_abbreviation_automatically_populates_with_qgenda_name(self):
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        self.assertEqual(provider.display_name, 'ProvA')

    def test_str_method(self):
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        self.assertEqual(provider.__str__(), 'ProvA')

    def test_can_change_provider_abbreviation_to_unique_value(self):
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvB')
        provider.display_name = 'Provider______B'
        provider.save()
        self.assertEqual(provider.display_name, 'Provider______B')

    def test_cannot_change_provider_abbreviation_to_non_unique_value(self):
        Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvA')
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='ProvB')
        provider.display_name = 'ProvA'
        with self.assertRaises(IntegrityError):
            provider.save()


class RoleTests(TestCase):
    def test_can_create_role_from_qgenda_name(self):
        self.assertEqual(Role.objects.count(), 0)
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        self.assertEqual(Role.objects.count(), 1)
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleB')
        self.assertEqual(Role.objects.count(), 2)

    def test_get_or_create_from_qgenda_name_returns_existing_role_if_role_already_created(self):
        self.assertEqual(Role.objects.count(), 0)
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        self.assertEqual(Role.objects.count(), 1)
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        self.assertEqual(Role.objects.count(), 1)

    def test_abbreviation_automatically_populates_with_qgenda_name(self):
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        self.assertEqual(role.display_name, 'RoleA')

    def test_str_method(self):
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        self.assertEqual(role.__str__(), 'RoleA')

    def test_can_change_role_abbreviation_to_unique_value(self):
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleB')
        role.display_name = 'Role______B'
        role.save()
        self.assertEqual(role.display_name, 'Role______B')

    def test_cannot_change_role_abbreviation_to_non_unique_value(self):
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleA')
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RoleB')
        role.display_name = 'RoleA'
        with self.assertRaises(IntegrityError):
            role.save()

    def test_rounder_role_created_automatically_if_starts_with_DOC(self):
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC32')
        self.assertIsInstance(role, RounderRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC23')
        self.assertIsInstance(role, RounderRole)
        self.assertEqual(RounderRole.objects.count(), 2)
        self.assertEqual(Role.objects.count(), 2)

    def test_secondary_role_created_automatically_if_starts_with_APP_MD_RISK_or_other(self):
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='AM TRIAGE')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='PM TRIAGE')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='SWING')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='PM ADMITTER')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='PTO/VACATION 1')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RISK2')
        self.assertIsInstance(role, SecondaryRole)
        role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='RISK2')
        self.assertIsInstance(role, SecondaryRole)
        self.assertEqual(SecondaryRole.objects.count(), 6)
        self.assertEqual(Role.objects.count(), 6)

    def test_rounder_roles_sort_such_that_DOC1_before_DOC5_before_DOC10_before_APP1_before_APP4_before_APP10(self):
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC5')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC11')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC10')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC32')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC1')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC2')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC22')
        Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC14')
        self.assertEqual(RounderRole.objects.count(), 8)
        expected_sorted_roles = ['DOC1', 'DOC2', 'DOC5', 'DOC10', 'DOC11', 'DOC14', 'DOC22', 'DOC32']
        sorted_by_initial_key = sorted([role for role in RounderRole.objects.all()],
                                       key=lambda rounderrole: rounderrole.initial_sort_key)
        self.assertEqual(expected_sorted_roles, [role.qgenda_name for role in sorted_by_initial_key])


class DistributionModelTests(TestCase):
    def test_can_create_distribution(self):
        Distribution.objects.create(date=timezone.localdate())
        self.assertEqual(Distribution.objects.count(), 1)

    def test_str_method(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        self.assertEqual(distribution.__str__(),
                         f"distribution_{timezone.localdate().strftime('%m/%d/%y')}_{timezone.localtime().strftime('%H:%M')}")


class DistributionModelMethodTests(TestCase):
    def test_can_assign_line_item_batting_order_from_initial_sort_key(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        role = Role.objects.get_or_create_from_qgenda_name('DOC5')
        li_1 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_1.assign_role(role)
        provider = Provider.objects.create(display_name='provB')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC56')
        li_2 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_2.assign_role(role)
        provider = Provider.objects.create(display_name='provC')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('RISK1')
        li_3 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_3.assign_role(role)
        provider = Provider.objects.create(display_name='provD')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC1')
        li_4 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_4.assign_role(role)
        distribution.assign_line_item_batting_order_from_initial_sort_key()
        self.assertEqual(distribution.line_items.get(provider__display_name='provA').position_in_batting_order, 2)
        self.assertEqual(distribution.line_items.get(provider__display_name='provB').position_in_batting_order, 3)
        self.assertEqual(distribution.line_items.get(provider__display_name='provC').position_in_batting_order, None)
        self.assertEqual(distribution.line_items.get(provider__display_name='provD').position_in_batting_order, 1)

    def test_can_return_queryset_of_ordered_rounder_line_items_ordered_by_position_in_rounding_order(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        role = Role.objects.get_or_create_from_qgenda_name('DOC5')
        li_1 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_1.assign_role(role)
        provider = Provider.objects.create(display_name='provB')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC56')
        li_2 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_2.assign_role(role)
        provider = Provider.objects.create(display_name='provC')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('RISK1')
        li_3 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_3.assign_role(role)
        provider = Provider.objects.create(display_name='provD')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC1')
        li_4 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_4.assign_role(role)
        distribution.assign_line_item_batting_order_from_initial_sort_key()
        ordered_line_items = distribution.return_ordered_rounder_line_items()
        self.assertEqual(ordered_line_items.count(), 3)
        self.assertEqual(ordered_line_items[0].provider.display_name, 'provD')
        self.assertEqual(ordered_line_items[1].provider.display_name, 'provA')
        self.assertEqual(ordered_line_items[2].provider.display_name, 'provB')

    def test_can_return_queryset_of_distribution_rounders_ordered_alphabetically(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        role = Role.objects.get_or_create_from_qgenda_name('DOC5')
        li_1 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_1.assign_role(role)
        provider = Provider.objects.create(display_name='provB')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC56')
        li_2 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_2.assign_role(role)
        provider = Provider.objects.create(display_name='provC')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('RISK1')
        li_3 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_3.assign_role(role)
        provider = Provider.objects.create(display_name='provD')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        role = Role.objects.get_or_create_from_qgenda_name('DOC1')
        li_4 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                         provider=provider)
        li_4.assign_role(role)
        alphabetical_rounders = distribution.return_alphabetical_rounders()
        self.assertEqual(['provA', 'provB', 'provD'],
                         [rounder.display_name for rounder in alphabetical_rounders])

    def test_can_make_next_up_ie_move_rounder_to_top_of_order(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provB', 'provC', 'provA', 'provD'])
        distribution.move_line_item_to_next_up(
            next_up_line_item=DistributionLineItem.objects.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provD', 'provB', 'provC', 'provA'])
        distribution.move_line_item_to_next_up(
            next_up_line_item=DistributionLineItem.objects.get(provider__display_name='provB'))
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provB', 'provC', 'provA', 'provD'])
        distribution.move_line_item_to_next_up(
            next_up_line_item=DistributionLineItem.objects.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provA', 'provD', 'provB', 'provC'])
        distribution.move_line_item_to_next_up(
            next_up_line_item=DistributionLineItem.objects.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provA', 'provD', 'provB', 'provC'])
        distribution.move_line_item_to_next_up(
            next_up_line_item=DistributionLineItem.objects.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provD', 'provB', 'provC', 'provA'])

    def test_shift_up_in_batting_order_switches_batting_order_with_line_item_above_if_position_in_bo_gt_1(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC', 'provA', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provA', 'provC', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA','provB',  'provC', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provB',  'provD','provC'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provD','provB',  'provC'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provB'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provB', 'provD', 'provC'])

    def test_shift_up_in_batting_order_does_nothing_if_position_in_batting_order_is_1(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC', 'provA', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provB'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC', 'provA', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provA', 'provC', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         [ 'provA','provB', 'provC', 'provD'])

        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provB', 'provC', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provB', 'provC', 'provD'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provB',  'provD','provC'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provA', 'provD','provB',  'provC'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provD','provA', 'provB',  'provC'])
        distribution.shift_up_in_batting_order(
            rising_line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provD','provA', 'provB',  'provC'])

    def test_delete_rounder_deletes_line_item_and_shifts_later_rounders_up_in_batting_order(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC', 'provA', 'provD'])
        self.assertEqual([line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
                         [1,2,3,4])
        distribution.delete_rounder(line_item=distribution.line_items.get(provider__display_name='provA'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC', 'provD'])
        self.assertEqual([line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
                         [1,2,3])
        distribution.delete_rounder(line_item=distribution.line_items.get(provider__display_name='provD'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provB', 'provC'])
        self.assertEqual([line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
                         [1,2])
        distribution.delete_rounder(line_item=distribution.line_items.get(provider__display_name='provB'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         ['provC'])
        self.assertEqual([line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
                         [1])
        distribution.delete_rounder(line_item=distribution.line_items.get(provider__display_name='provC'))
        self.assertEqual([line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
                         [])
        self.assertEqual([line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
                         [])


class DistributionLineItemModelTests(TestCase):
    def test_can_create_line_item_given_provider_and_distribution(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        provider = Provider.objects.create(display_name='provB')
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        self.assertEqual(DistributionLineItem.objects.count(), 2)

    def test_str_method(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                  provider=provider)
        line_item = DistributionLineItem.objects.first()
        self.assertEqual(line_item.__str__(), 'non-rounder provA')
        rounder_role = Role.objects.get_or_create_from_qgenda_name('DOC23')
        line_item.rounder_role = rounder_role
        line_item.save()
        self.assertEqual(line_item.__str__(), 'DOC23 provA')

    def test_attempting_to_create_line_item_with_same_provider_gets_same_line_item(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        li1 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                        provider=provider)
        li2 = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                        provider=provider)
        self.assertEqual(DistributionLineItem.objects.count(), 1)
        self.assertEqual(li1, li2)

    def test_can_assign_rounder_role_to_line_item(self):
        rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC45')
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        line_item.assign_role(role=rounder_role)
        self.assertEqual(line_item.rounder_role, rounder_role)

    def test_attempting_to_assign_second_rounder_role_to_line_item_overwrites_first_rounder_role(self):
        rounder_role_45 = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC45')
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        line_item.assign_role(role=rounder_role_45)
        self.assertEqual(rounder_role_45.line_items.count(), 1)
        rounder_role_5 = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC5')
        line_item.assign_role(role=rounder_role_5)
        self.assertEqual(rounder_role_5.line_items.count(), 1)
        self.assertEqual(rounder_role_45.line_items.count(), 0)
        self.assertEqual(line_item.rounder_role, rounder_role_5)

    def test_assigning_rounder_role_that_is_assigned_to_different_line_item_removes_the_rounder_role_from_prior(self):
        rounder_role_45 = Role.objects.get_or_create_from_qgenda_name(qgenda_name='DOC45')
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        line_item.assign_role(role=rounder_role_45)
        prov_b = Provider.objects.create(display_name='provB')
        line_item_b = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=prov_b)
        line_item_b.assign_role(role=rounder_role_45)
        self.assertEqual(rounder_role_45.line_items.count(), 1)
        self.assertEqual(rounder_role_45.line_items.all()[0], line_item_b)
        line_item = DistributionLineItem.objects.first()
        self.assertIsNone(line_item.rounder_role)
        self.assertEqual(line_item_b.rounder_role, rounder_role_45)

    def test_can_assign_secondary_role_to_line_item(self):
        pm_triage_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='pm triage')
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        line_item.assign_role(role=pm_triage_role)
        self.assertEqual(line_item.secondary_roles_for_line_items.count(), 1)
        secondary_roles = [merge_table_entry.secondary_role for merge_table_entry in
                           line_item.secondary_roles_for_line_items.all()]
        self.assertEqual(secondary_roles[0], pm_triage_role)

    def test_can_assign_two_secondary_roles_to_line_item(self):
        pm_triage_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='pm triage')
        app_md_1_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='app_md_1')
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        line_item.assign_role(role=pm_triage_role)
        line_item.assign_role(role=app_md_1_role)
        self.assertEqual(line_item.secondary_roles_for_line_items.count(), 2)
        line_item_secondary_roles = [merge_table_entry.secondary_role for merge_table_entry in
                                     line_item.secondary_roles_for_line_items.all()]
        self.assertEqual(line_item_secondary_roles, [pm_triage_role, app_md_1_role])


class DistributionManagerMethodTests(TestCase):

    # testing create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data()

    def test_create_from_relevant_data_creates_new_provider_for_each_unique_qgenda_staffabbrev(self):
        self.assertEqual(Provider.objects.count(), 0)
        Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(Provider.objects.count(), 16)

    def test_create_from_relevant_data_creates_new_role_for_each_unique_qgenda_taskname(self):
        self.assertEqual(Role.objects.count(), 0)
        Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(Role.objects.count(), 19)

    def test_create_from_relevant_data_creates_new_line_item_for_each_unique_provider_in_dict(self):
        self.assertEqual(Role.objects.count(), 0)
        Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(DistributionLineItem.objects.count(), 16)

    def test_create_from_relevant_data_returns_new_distribution(self):
        self.assertEqual(Distribution.objects.count(), 0)
        return_val = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertIsInstance(return_val, Distribution)

    def test_create_from_relevant_data_creates_line_items_linked_to_distribution_provider_role(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(distribution.line_items.count(), 16)

    def test_create_from_relevant_data_creates_line_items_that_can_be_filtered_by_rounder_role(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(distribution.line_items.filter(rounder_role__isnull=False).count(), 9)

    def test_create_from_relevant_data_assigns_value_to_position_in_batting_order_based_initially_on_rounder_role(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        for index, line_item in enumerate(distribution.line_items.filter(rounder_role__isnull=False)):
            self.assertEqual(line_item.position_in_batting_order, index + 1)

    def test_create_from_relevant_data_creates_blank_starting_census_for_each_rounder_role(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        for index, line_item in enumerate(distribution.line_items.filter(rounder_role__isnull=False)):
            self.assertIsInstance(line_item.startingcensus, StartingCensus)
            self.assertEqual(line_item.startingcensus.total_census, None)
            self.assertEqual(line_item.startingcensus.CCU_census, None)
            self.assertEqual(line_item.startingcensus.COVID_census, None)

    def test_create_from_relevant_data_creates_line_item_with_secondary_role_of_triage(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        triage_line_items = distribution.line_items.filter(
            secondary_roles_for_line_items__secondary_role__qgenda_name__endswith='TRIAGE')
        self.assertEqual(triage_line_items.count(), 2)
        for line_item in triage_line_items:
            self.assertTrue(line_item.secondary_roles_for_line_items.filter(
                secondary_role__qgenda_name__endswith='TRIAGE').first().secondary_role.display_name.endswith('TRIAGE'))

    def test_create_new_on_view_load_method_returns_distribution_instance(self):
        distribution = Distribution.objects.get_last_for_date_or_create_new(date=timezone.localdate())
        self.assertIsInstance(distribution, Distribution)

    def test_create_new_on_view_load_method_returns_last_distribution_for_date_if_one_exists(self):
        existing_distribution = Distribution.objects.create(date=timezone.localdate())
        returned_distribution = Distribution.objects.get_last_for_date_or_create_new(date=timezone.localdate())
        self.assertEqual(existing_distribution, returned_distribution)

    def test_create_new_on_view_load_method_returns_distribution_with_qgenda_data_if_none_exists_for_date(self):
        returned_distribution = Distribution.objects.get_last_for_date_or_create_new(date=timezone.localdate())
        self.assertIsInstance(returned_distribution, Distribution)
        self.assertGreater(returned_distribution.line_items.count(), 10)


class QGendaDataSetTests(TestCase):
    def test_can_create_qgenda_dataset(self):
        QGendaDataSet.objects.create(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.count(), 1)

    def test_str_method(self):
        dataset = QGendaDataSet.objects.create(date=timezone.localdate())
        self.assertEqual(
            dataset.__str__(),
            f"qgenda_dataset_{timezone.localdate().strftime('%m/%d/%y')}_{timezone.localtime().strftime('%H:%M')}")


class QGendaDataSetManagerMethodTests(TestCase):

    def test_get_updated_dataset_method_default_behavior_creates_new_dataset_if_none_exists_for_date(self):
        self.assertEqual(QGendaDataSet.objects.count(), 0)
        QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.count(), 1)

    def test_get_updated_dataset_method_default_behavior_returns_last_dataset_if_one_created_within_60_mins(self):
        with mock.patch('distribution.models.timezone.localtime',
                        return_value=timezone.localtime() - timezone.timedelta(minutes=59)):
            non_stale_data_set = QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.filter(date=timezone.localdate()).count(), 1)
        QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.filter(date=timezone.localdate()).count(), 1)

    def test_get_updated_dataset_method_default_behavior_returns_new_dataset_if_last_created_outside_of_60_mins(self):
        with mock.patch('distribution.models.timezone.localtime',
                        return_value=timezone.localtime() - timezone.timedelta(minutes=60)):
            stale_data_set = QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.filter(date=timezone.localdate()).count(), 1)
        QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.filter(date=timezone.localdate()).count(), 2)

    def test_create_new_dataset_method_gets_new_dataset_even_if_recent_dataset(self):
        QGendaDataSet.objects.get_updated_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.count(), 1)
        QGendaDataSet.objects.create_new_dataset(date=timezone.localdate())
        self.assertEqual(QGendaDataSet.objects.count(), 2)


class StartingCensusTests(TestCase):
    def test_can_create_starting_census_with_distribution_line_item_total_census_COVID_census_and_CCU_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        starting_census = StartingCensus.objects.create(distribution_line_item=line_item, total_census=12, CCU_census=3,
                                                        COVID_census=2)

    def test_str_method(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        starting_census = StartingCensus.objects.create(distribution_line_item=line_item, total_census=12, CCU_census=3,
                                                        COVID_census=2)
        self.assertEqual(starting_census.__str__(), 'provA starting census - 12(3)[2]')


class PostBounceCensusTests(TestCase):
    def test_can_create_post_bounce_census_with_distribution_line_item_total_census_COVID_census_and_CCU_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        post_bounce_census = PostBounceCensus.objects.create(distribution_line_item=line_item, total_census=12,
                                                             CCU_census=3,
                                                             COVID_census=2)

    def test_str_method(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        post_bounce_census = PostBounceCensus.objects.create(distribution_line_item=line_item, total_census=12,
                                                             CCU_census=3,
                                                             COVID_census=2)
        self.assertEqual(post_bounce_census.__str__(), 'provA post-bounce census - 12(3)[2]')


class PatientTests(TestCase):
    def test_can_create_patient(self):
        Patient.objects.create(
            distribution=Distribution.objects.create(date=timezone.localdate()), number_designation=1)

class DistributionEmailTests(TestCase):
    def test_can_create_distribution_email(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email = DistributionEmail.objects.create(distribution=distribution)
        self.assertEqual(DistributionEmail.objects.count(), 1)






    def test_can_send_distribution_email(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        recipients = ['fake@kalusinator.com', 'fake@kalusinator.com', 'fake@kalusinator.com']
        email = DistributionEmail.objects.create(distribution=distribution, recipient_text_field=recipients)
        email.send_distribution_email()
        self.assertEqual(len(mail.outbox), 1)

