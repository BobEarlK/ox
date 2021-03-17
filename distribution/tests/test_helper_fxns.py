from django.test import TestCase

from ..helper_fxns import helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items, \
    helper_fxn_add_4_non_rounder_line_items_to_distribution
from ..models import Distribution, DistributionLineItem, RounderRole, Provider, StartingCensus


class CreateDistributionTests(TestCase):
    def test_helper_fxn_creates_distribution(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.assertEqual(Distribution.objects.count(), 1)

    def test_helper_fxn_creates_line_items_roles_providers_starting_censuses(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.assertEqual(DistributionLineItem.objects.count(), 6)
        self.assertEqual(RounderRole.objects.count(), 4)
        self.assertEqual(Provider.objects.count(), 6)
        self.assertEqual(StartingCensus.objects.count(), 4)

    def test_helper_fxn_creates_non_rounder_line_items(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.assertEqual(DistributionLineItem.objects.count(), 6)
        self.assertEqual(DistributionLineItem.objects.filter(rounder_role__isnull=True).count(), 2)
        self.assertEqual(DistributionLineItem.objects.filter(rounder_role__isnull=False).count(), 4)

    def test_helper_fxn_orders_rounder_line_items_by_batting_order(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        expected_providers = ['provB', 'provC', 'provA', 'provD']
        distribution = Distribution.objects.first()
        self.assertEqual(expected_providers, [line_item.provider.display_name
                                              for line_item in distribution.return_ordered_rounder_line_items()])

class AddNonRounderLineItemTests(TestCase):
    def test_helper_fxn_adds_line_items(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        helper_fxn_add_4_non_rounder_line_items_to_distribution(distribution=distribution)
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(distribution.line_items.count(), 8)

    def test_helper_fxn_does_not_add_rounder_line_items(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        helper_fxn_add_4_non_rounder_line_items_to_distribution(distribution=distribution)
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)