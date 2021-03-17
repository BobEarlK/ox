from django.test import TestCase
from django.utils import timezone

from ..helper_fxns import helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items
from ..models import Distribution, Patient, Provider, Role, DistributionLineItem, StartingCensus, AllocatedCensus, \
    AssignedCensus, PostBounceCensus


class AssignBouncebackPatientsTests(TestCase):
    def test_can_assign_bounceback_patient_that_even_if_over_quota(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        for i in range(8):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=True, CCU=True,
                                   bounce_to=Provider.objects.get(display_name='provA'))
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_bounceback_patients()
        expected_post_bounce_total_censuses = [11, 13, 18, 11]
        actual_post_bounce_total_censuses = [line_item.postbouncecensus.total_census for line_item in
                                             distribution.return_ordered_rounder_line_items()]
        self.assertEqual(actual_post_bounce_total_censuses, expected_post_bounce_total_censuses)
        for patient in Patient.objects.all():
            self.assertEqual(patient.distribution_line_item.provider.display_name, 'provA')

    def test_assigning_bounceback_patient_increments_allocatedcensus_and_assignedcensus(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        actual_starting_CCU_censuses = [line_item.startingcensus.CCU_census for line_item in
                                        distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_CCU_censuses, actual_starting_CCU_censuses)
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_COVID_censuses = [line_item.startingcensus.COVID_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_COVID_censuses, actual_starting_COVID_censuses)
        for i in range(3):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=True, CCU=True,
                                   bounce_to=Provider.objects.get(display_name='provA'))
        for i in range(3):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=False, CCU=True,
                                   bounce_to=Provider.objects.get(display_name='provB'))
        for i in range(2):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=False, CCU=False,
                                   bounce_to=Provider.objects.get(display_name='provC'))
        for i in range(5):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=True, CCU=False,
                                   bounce_to=Provider.objects.get(display_name='provA'))
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_bounceback_patients()
        expected_assigned_total_censuses = [14, 15, 18, 11]
        actual_post_bounce_total_censuses = [line_item.postbouncecensus.total_census for line_item in
                                             distribution.return_ordered_rounder_line_items()]
        self.assertEqual(actual_post_bounce_total_censuses, expected_assigned_total_censuses)
        expected_assigned_CCU_censuses = [6, 2, 5, 1]
        actual_post_bounce_CCU_censuses = [line_item.postbouncecensus.CCU_census for line_item in
                                           distribution.return_ordered_rounder_line_items()]
        self.assertEqual(actual_post_bounce_CCU_censuses, expected_assigned_CCU_censuses)
        expected_assigned_COVID_censuses = [3, 1, 8, 2]
        actual_post_bounce_COVID_censuses = [line_item.postbouncecensus.COVID_census for line_item in
                                             distribution.return_ordered_rounder_line_items()]
        self.assertEqual(actual_post_bounce_COVID_censuses, expected_assigned_COVID_censuses)


class AllocateTotalPatientTests(TestCase):
    def test_allocate_total_patients_allocates_single_patient_to_last_rounder_with_lowest_number_and_with_space(self):
        expected_post_allocation_censuses = [
            [11, 13, 10, 11],
            [11, 13, 11, 11],
            [11, 13, 11, 12],
            [11, 13, 12, 12],
            [12, 13, 12, 12],
            [12, 13, 12, 13],
            [12, 13, 13, 13],
            [13, 13, 13, 13],
            [13, 13, 13, 14],
            [13, 13, 14, 14],
            [13, 14, 14, 14],
            [14, 14, 14, 14],
            [14, 14, 14, 15],
            [14, 14, 15, 15],
            [14, 15, 15, 15],
            [15, 15, 15, 15],
            [15, 15, 15, 16],
            [15, 15, 16, 16],
            [15, 16, 16, 16],
            [16, 16, 16, 16],
            [16, 16, 16, 17],
            [16, 16, 17, 17],
            [16, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for total_patient_count in range(30):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            post_allocation_total_censuses = [line_item.allocatedcensus.total_census for line_item in
                                              distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_total_censuses, expected_post_allocation_censuses[total_patient_count])

    def test_allocate_total_patients_respects_altered_provider_maxima(self):
        expected_post_allocation_censuses = [
            [11, 13, 10, 11],
            [11, 13, 10, 12],
            [12, 13, 10, 12],
            [13, 13, 10, 12],
            [13, 14, 10, 12],
            [14, 14, 10, 12],
            [15, 14, 10, 12],
            [16, 14, 10, 12],
            [17, 14, 10, 12],
            [18, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
            [19, 14, 10, 12],
        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for total_patient_count in range(30):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                Patient.objects.create(distribution=distribution, number_designation=i + 1)
            arbitrary_maxima = [19, 14, 3, 12]
            for index, provider in enumerate(
                    [line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]):
                provider.max_total_census = arbitrary_maxima[index]
                provider.save()
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            post_allocation_total_censuses = [line_item.allocatedcensus.total_census for line_item in
                                              distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_total_censuses, expected_post_allocation_censuses[total_patient_count])


class AssignDualPositivePatients(TestCase):
    def test_return_single_highest_affinity_line_item_selects_high_COVID_CCU_values_if_others_have_no_room(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB']
        starting_totals = [10, 5]
        allocated_totals = [11, 5]  # only provA has room
        CCUs = [5, 0]
        COVIDs = [5, 0]
        for i in range(2):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        self.assertEqual(
            'provA',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)

    def test_return_single_highest_affinity_line_item_selects_lower_COVID_CCU_values_over_higher(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB']
        starting_totals = [10, 10]
        allocated_totals = [11, 11]  # both have room, prov B has fewer CCU, COVID
        CCUs = [5, 0]
        COVIDs = [5, 0]
        for i in range(2):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)

    def test_return_single_highest_affinity_line_item_selects_later_values(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB']
        starting_totals = [10, 10]
        allocated_totals = [11, 11]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [0, 5]
        COVIDs = [5, 0]
        for i in range(2):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)

    def test_return_single_highest_affinity_line_item_selects_later_line_items_if_all_other_factors_equal(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB']
        starting_totals = [10, 10]
        allocated_totals = [11, 11]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [2, 2]
        COVIDs = [3, 3]
        for i in range(2):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)

    def test_return_single_highest_affinity_line_item_increments_allocatedcensus_COVID_CCU_census(self):
        # Note:  but not total census, which has already been incremented by distribution.allocate_total_patient_count
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB']
        starting_totals = [10, 10]
        allocated_totals = [11, 11]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [2, 2]
        COVIDs = [3, 3]
        for i in range(2):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient()
        self.assertEqual(
            [line_item.allocatedcensus.total_census for line_item in distribution.return_ordered_rounder_line_items()],
            [11, 11])
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4]
        )
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 3]
        )

    def test_sequential_use_of_return_single_highest_affinity_line_item_returns_expected_values(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        self.assertEqual(
            'provD',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 1, 0, 1, 3, 1]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [0, 1, 0, 1, 1, 2]
        )
        self.assertEqual(
            'provC',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 1, 1, 1, 3, 1]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [0, 1, 1, 1, 1, 2]
        )
        self.assertEqual(
            'provA',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 1, 1, 1, 3, 1]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 1, 1, 1, 1, 2]
        )
        self.assertEqual(
            'provD',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 1, 1, 2, 3, 1]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 1, 1, 2, 1, 2]
        )
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 2, 1, 2, 3, 1]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 2, 1, 2, 1, 2]
        )
        self.assertEqual(
            'provF',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 2, 1, 2, 3, 2]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 2, 1, 2, 1, 3]
        )
        self.assertEqual(
            'provA',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 2, 1, 2, 3, 2]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 2, 1, 2, 1, 3]
        )
        self.assertEqual(
            'provD',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 2, 1, 3, 3, 2]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 2, 1, 3, 1, 3]
        )
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 3, 1, 3, 3, 2]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 3, 1, 3, 1, 3]
        )
        self.assertEqual(
            'provE',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 3, 1, 3, 4, 2]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 3, 1, 3, 2, 3]
        )
        self.assertEqual(
            'provF',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 3, 1, 3, 4, 3]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [2, 3, 1, 3, 2, 4]
        )
        self.assertEqual(
            'provA',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 3, 1, 3, 4, 3]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 3, 1, 3, 2, 4]
        )
        self.assertEqual(
            'provE',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 3, 1, 3, 5, 3]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 3, 1, 3, 3, 4]
        )
        self.assertEqual(
            'provB',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 5, 3]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 3, 4]
        )
        self.assertEqual(
            'provF',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 5, 4]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 3, 5]
        )
        self.assertEqual(
            'provE',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 6, 4]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 4, 5]
        )
        self.assertEqual(
            'provF',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 6, 5]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 4, 6]
        )
        self.assertEqual(
            'provE',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 7, 5]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 5, 6]
        )
        self.assertEqual(
            'provE',
            distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient().provider.display_name)
        self.assertEqual(
            [line_item.allocatedcensus.CCU_census for line_item in distribution.return_ordered_rounder_line_items()],
            [4, 4, 1, 3, 8, 5]
        )
        self.assertEqual(
            [line_item.allocatedcensus.COVID_census for line_item in distribution.return_ordered_rounder_line_items()],
            [3, 4, 1, 3, 6, 6]
        )
        self.assertIsNone(distribution.return_single_highest_affinity_line_item_and_allocate_dual_pos_patient())

    def test_return_highest_affinity_line_items_returns_num_line_items_equal_to_number_of_dual_pos_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, COVID=True, number_designation=i + 1)
        highest_affinity_line_items = distribution.return_line_items_for_dual_pos_assignment()
        self.assertEqual(len(highest_affinity_line_items), 7)

    def test_return_highest_affinity_line_items_returns_line_items_in_expected_order(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, COVID=True, number_designation=i + 1)
        highest_affinity_line_items = distribution.return_line_items_for_dual_pos_assignment()
        self.assertEqual(['provA', 'provA', 'provB', 'provC', 'provD', 'provD', 'provF'],
                         [line_item.provider.display_name for line_item in highest_affinity_line_items])

    def test_assign_dual_pos_patients_adds_patients_to_line_items(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, COVID=True, number_designation=i + 1)
        for i in range(12):
            Patient.objects.create(distribution=distribution, CCU=False, COVID=False, number_designation=i + 8)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.allocate_total_patients()
        distribution.assign_dual_positive_patients()
        self.assertEqual(['provA', 'provA', 'provB', 'provC', 'provD', 'provD', 'provF'],
                         [patient.distribution_line_item.provider.display_name for patient in
                          distribution.patients.filter(COVID=True, CCU=True)])

    def test_assign_dual_pos_patients_increments_assigned_censuses_total_CCU_and_COVID(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, COVID=True, number_designation=i + 1)
        for i in range(12):
            Patient.objects.create(distribution=distribution, CCU=False, COVID=False, number_designation=i + 8)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.allocate_total_patients()
        distribution.assign_dual_positive_patients()
        expected_total_censuses = [12, 11, 13, 13, 9, 11]
        expected_CCU_censuses = [3, 2, 1, 2, 3, 2]
        expected_COVID_censuses = [2, 2, 1, 2, 1, 3]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.allocatedcensus.CCU_census, expected_CCU_censuses[index])
            self.assertEqual(line_item.allocatedcensus.COVID_census, expected_COVID_censuses[index])
            self.assertEqual(line_item.assignedcensus.total_census, expected_total_censuses[index])
            self.assertEqual(line_item.assignedcensus.CCU_census, expected_CCU_censuses[index])
            self.assertEqual(line_item.assignedcensus.COVID_census, expected_COVID_censuses[index])


class AssignCCUPatientTests(TestCase):
    def test_allocate_CCU_patients_allocates_single_patient_to_last_rounder_with_lowest_number_if_allocated_total_pt(
            self):
        # testing as if total of 6 patients assigned, which would have been assigned [1,0,3,2]; can't allocate beyond
        # max total number assigned
        expected_post_allocation_censuses = [
            [3, 2, 2, 1],
            [3, 2, 2, 2],
            [3, 2, 2, 3],
            [3, 2, 3, 3],
            [3, 2, 4, 3],
            [4, 2, 4, 3],
            [4, 2, 5, 3]
        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        total_patient_count = 6
        for CCU_patient_count in range(6):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                if i < CCU_patient_count:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1, CCU=True)
                else:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_CCU_positive_patients()
            post_allocation_CCU_censuses = [line_item.allocatedcensus.CCU_census for line_item in
                                            distribution.return_ordered_rounder_line_items()]
            post_assignment_CCU_censuses = [line_item.assignedcensus.CCU_census for line_item in
                                            distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_CCU_censuses, expected_post_allocation_censuses[CCU_patient_count])
            self.assertEqual(post_assignment_CCU_censuses, expected_post_allocation_censuses[CCU_patient_count])

    def test_allocate_CCU_patients_with_higher_total_patients_allocated(self):
        # testing as if total of 15 patients assigned, which would have been assigned [4,2,5,4]; can't allocate beyond
        # max total number assigned
        expected_post_allocation_censuses = [
            [3, 2, 2, 1],
            [3, 2, 2, 2],
            [3, 2, 2, 3],
            [3, 2, 3, 3],
            [3, 3, 3, 3],
            [3, 3, 3, 4],
            [3, 3, 4, 4],
            [3, 4, 4, 4],
            [4, 4, 4, 4],
            [4, 4, 4, 5],
            [4, 4, 5, 5],
            [5, 4, 5, 5],
            [5, 4, 6, 5],
            [6, 4, 6, 5],
            [6, 4, 7, 5],
            [7, 4, 7, 5],
            [7, 4, 7, 5],
            [7, 4, 7, 5],

        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        total_patient_count = 15
        for CCU_patient_count in range(18):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                if i < CCU_patient_count:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1, CCU=True)
                else:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_CCU_positive_patients()
            post_allocation_CCU_censuses = [line_item.allocatedcensus.CCU_census for line_item in
                                            distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_CCU_censuses, expected_post_allocation_censuses[CCU_patient_count])

    def test_allocate_CCU_patients_respects_altered_provider_maxima(self):
        # testing as if total of 15 patients assigned, which would have been assigned [4,2,5,4]; can't allocate beyond
        # max total number assigned
        expected_post_allocation_censuses = [
            [3, 2, 2, 1],
            [3, 2, 2, 2],
            [3, 2, 2, 3],
            [3, 2, 3, 3],
            [3, 2, 3, 4],
            [3, 2, 4, 4],
            [4, 2, 4, 4],
            [4, 2, 4, 5],
            [4, 2, 5, 5],
            [5, 2, 5, 5],
        ]

        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        arbitrary_maxima = [5, 0, 5, 6]
        for index, provider in enumerate(
                [line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]):
            provider.max_CCU_census = arbitrary_maxima[index]
            provider.save()
        total_patient_count = 15
        for CCU_patient_count in range(10):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                if i < CCU_patient_count:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1, CCU=True)
                else:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_CCU_positive_patients()
            post_allocation_CCU_censuses = [line_item.allocatedcensus.CCU_census for line_item in
                                            distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_CCU_censuses, expected_post_allocation_censuses[CCU_patient_count])

    def test_assign_CCU_pos_patients_adds_patients_to_line_items(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_CCU_positive_patients()
        self.assertEqual(['provA', 'provB', 'provC', 'provD', 'provD', 'provF', 'provF'],
                         [patient.distribution_line_item.provider.display_name for patient in
                          distribution.patients.filter(COVID=False, CCU=True)])

    def test_assign_CCU_pos_patients_increments_assigned_total_and_CCU_censuses(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, CCU=True, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_CCU_positive_patients()
        expected_total_censuses = [11, 11, 13, 13, 9, 12]
        expected_CCU_censuses = [2, 2, 1, 2, 3, 3]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.allocatedcensus.CCU_census, expected_CCU_censuses[index])
            self.assertEqual(line_item.assignedcensus.total_census, expected_total_censuses[index])
            self.assertEqual(line_item.assignedcensus.CCU_census, expected_CCU_censuses[index])


class AssignCOVIDPositiveTests(TestCase):
    def test_can_allocate_0_to_15_COVID_patients_correctly_out_of_15_total_patients(self):
        # testing as if total of 15 patients assigned, which would have been assigned [4,2,5,4]; can't allocate beyond
        # max total number assigned
        expected_post_allocation_COVID_censuses = [
            [3, 1, 0, 2],
            [3, 1, 1, 2],
            [3, 1, 2, 2],
            [3, 2, 2, 2],
            [3, 2, 2, 3],
            [3, 2, 3, 3],
            [3, 3, 3, 3],
            [3, 3, 3, 4],
            [3, 3, 4, 4],
            [4, 3, 4, 4],
            [4, 3, 4, 5],
            [4, 3, 5, 5],
            [5, 3, 5, 5],
            [5, 3, 5, 6],
            [6, 3, 5, 6],
            [7, 3, 5, 6],
            [7, 3, 5, 6],
            [7, 3, 5, 6]
        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        total_patient_count = 15
        for COVID_patient_count in range(18):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                if i < COVID_patient_count:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=True)
                else:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_COVID_positive_patients()
            post_allocation_COVID_censuses = [line_item.allocatedcensus.COVID_census for line_item in
                                              distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_COVID_censuses,
                             expected_post_allocation_COVID_censuses[COVID_patient_count])

    def test_allocate_COVID_patients_respects_altered_provider_maxima(self):
        # testing as if total of 15 patients assigned, which would have been assigned [4,2,5,4]; can't allocate beyond
        # max total number assigned
        expected_post_allocation_COVID_censuses = [
            [3, 1, 0, 2],
            [3, 1, 1, 2],
            [3, 1, 2, 2],
            [3, 2, 2, 2],
            [3, 2, 2, 3],
            [3, 2, 3, 3],
            [3, 3, 3, 3],
            [3, 3, 3, 4],
            [3, 3, 4, 4],
            [3, 3, 4, 5],
            [3, 3, 5, 5],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
            [3, 3, 5, 6],
        ]

        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        arbitrary_maxima = [0, 17, 12, 17]
        for index, provider in enumerate(
                [line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]):
            provider.max_COVID_census = arbitrary_maxima[index]
            provider.save()
        total_patient_count = 15
        for COVID_patient_count in range(18):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                if i < COVID_patient_count:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=True)
                else:
                    Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_COVID_positive_patients()
            post_allocation_COVID_censuses = [line_item.allocatedcensus.COVID_census for line_item in
                                              distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_COVID_censuses,
                             expected_post_allocation_COVID_censuses[COVID_patient_count])

    def test_assign_COVID_pos_patients_adds_patients_to_line_items(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, COVID=True, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_COVID_positive_patients()
        self.assertEqual(['provA', 'provA', 'provB', 'provC', 'provD', 'provD', 'provE'],
                         [patient.distribution_line_item.provider.display_name for patient in
                          distribution.patients.filter(COVID=True, CCU=False)])

    def test_assign_COVID_pos_patients_increments_assigned_COVID_and_total_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        allocated_totals = [13, 13, 13, 14, 14, 14]  # both have room, prov A has fewer CCU, B has fewer COVID
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, COVID=True, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_COVID_positive_patients()
        expected_total_censuses = [12, 11, 13, 13, 10, 10]
        expected_COVID_censuses = [2, 2, 1, 2, 2, 2]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.allocatedcensus.COVID_census, expected_COVID_censuses[index])
            self.assertEqual(line_item.assignedcensus.total_census, expected_total_censuses[index])
            self.assertEqual(line_item.assignedcensus.COVID_census, expected_COVID_censuses[index])


class AssignDualNegativeTests(TestCase):
    def test_can_allocate_0_to_30_dual_neg_patients(self):
        expected_total_censuses = [
            [11, 13, 10, 11],
            [11, 13, 11, 11],
            [11, 13, 11, 12],
            [11, 13, 12, 12],
            [12, 13, 12, 12],
            [12, 13, 12, 13],
            [12, 13, 13, 13],
            [13, 13, 13, 13],
            [13, 13, 13, 14],
            [13, 13, 14, 14],
            [13, 14, 14, 14],
            [14, 14, 14, 14],
            [14, 14, 14, 15],
            [14, 14, 15, 15],
            [14, 15, 15, 15],
            [15, 15, 15, 15],
            [15, 15, 15, 16],
            [15, 15, 16, 16],
            [15, 16, 16, 16],
            [16, 16, 16, 16],
            [16, 16, 16, 17],
            [16, 16, 17, 17],
            [16, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
            [17, 17, 17, 17],
        ]
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for total_patient_count in range(30):
            distribution.patients.all().delete()
            for i in range(total_patient_count):
                Patient.objects.create(distribution=distribution, number_designation=i + 1)
            distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
            distribution.allocate_total_patients()
            distribution.assign_dual_negative_patients()
            post_allocation_total_censuses = [line_item.allocatedcensus.total_census for line_item in
                                              distribution.return_ordered_rounder_line_items()]
            self.assertEqual(post_allocation_total_censuses,
                             expected_total_censuses[total_patient_count])

    def test_assign_dual_neg_patients_adds_patients_to_line_items(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        allocated_totals = [12, 10, 13, 14, 9, 11]  # both have room, prov A has fewer CCU, B has fewer COVID
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_dual_negative_patients()
        self.assertEqual(['provA', 'provA', 'provC', 'provD', 'provD', 'provD', 'provF'],
                         [patient.distribution_line_item.provider.display_name for patient in
                          distribution.patients.filter(COVID=False, CCU=False).order_by('number_designation')])

    def test_assign_dual_neg_patients_increments_assigned_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF']
        starting_totals = [10, 10, 12, 11, 9, 10]
        CCUs = [1, 1, 0, 0, 3, 1]
        COVIDs = [0, 1, 0, 0, 1, 2]
        allocated_totals = [12, 10, 13, 14, 9, 11]  # both have room, prov A has fewer CCU, B has fewer COVID
        for i in range(6):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i + 1}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = i + 1
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
            AllocatedCensus.objects.create(distribution_line_item=line_item, total_census=allocated_totals[i],
                                           CCU_census=CCUs[i],
                                           COVID_census=COVIDs[i])
            AssignedCensus.objects.create(distribution_line_item=line_item, total_census=starting_totals[i],
                                          CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(7):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
        for patient in distribution.patients.all():
            self.assertIsNone(patient.distribution_line_item)
        distribution.assign_dual_negative_patients()
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.assignedcensus.total_census, allocated_totals[index])


class AssignMixedBagOfPatients(TestCase):
    def test_can_assign_bounceback_patient_and_dual_negative(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=1, COVID=True, CCU=True,
                               bounce_to=Provider.objects.get(display_name='provA'))
        Patient.objects.create(distribution=distribution, number_designation=2)
        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [11, 13, 11, 12]
        expected_assigned_CCU_censuses = [3, 2, 3, 1]
        expected_assigned_COVID_censuses = [3, 1, 1, 2]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_bounceback_patient_and_dual_positive(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=1, COVID=True, CCU=True,
                               bounce_to=Provider.objects.get(display_name='provA'))
        Patient.objects.create(distribution=distribution, COVID=True, CCU=True, number_designation=2)
        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [11, 13, 11, 12]
        expected_assigned_CCU_censuses = [3, 2, 3, 2]
        expected_assigned_COVID_censuses = [3, 1, 1, 3]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_one_of_all_COVID_CCU_permutations(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=1, COVID=False, CCU=False)
        Patient.objects.create(distribution=distribution, COVID=True, CCU=True, number_designation=2)
        Patient.objects.create(distribution=distribution, COVID=True, number_designation=3)
        Patient.objects.create(distribution=distribution, CCU=True, number_designation=4)
        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [12, 13, 12, 12]
        expected_assigned_CCU_censuses = [3, 2, 3, 2]
        expected_assigned_COVID_censuses = [3, 1, 2, 2]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_four_of_all_COVID_CCU_permutations(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        for i in range(4):
            Patient.objects.create(distribution=distribution, number_designation=1 + 4 * i, COVID=False, CCU=False)
            Patient.objects.create(distribution=distribution, COVID=True, CCU=True, number_designation=2 + 4 * i)
            Patient.objects.create(distribution=distribution, COVID=True, number_designation=3 + 4 * i)
            Patient.objects.create(distribution=distribution, CCU=True, number_designation=4 + 4 * 1)
        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [15, 15, 15, 16]
        expected_assigned_CCU_censuses = [4, 3, 4, 5]
        expected_assigned_COVID_censuses = [3, 3, 4, 4]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_two_bounces_and_four_of_all_COVID_CCU_permutations(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=17, CCU=True,
                               bounce_to=Provider.objects.get(display_name='provA'))
        Patient.objects.create(distribution=distribution, number_designation=18, CCU=True, COVID=True,
                               bounce_to=Provider.objects.get(display_name='provC'))
        for i in range(4):
            Patient.objects.create(distribution=distribution, number_designation=1 + 4 * i, COVID=False, CCU=False)
            Patient.objects.create(distribution=distribution, COVID=True, CCU=True, number_designation=2 + 4 * i)
            Patient.objects.create(distribution=distribution, COVID=True, number_designation=3 + 4 * i)
            Patient.objects.create(distribution=distribution, CCU=True, number_designation=4 + 4 * 1)
        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [15, 16, 16, 16]
        expected_assigned_CCU_censuses = [4, 4, 5, 5]
        expected_assigned_COVID_censuses = [3, 4, 4, 4]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_two_bounces_and_a_typical_large_distribution(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=17, CCU=True,
                               bounce_to=Provider.objects.get(display_name='provA'))
        Patient.objects.create(distribution=distribution, number_designation=18, CCU=True, COVID=True,
                               bounce_to=Provider.objects.get(display_name='provC'))
        for i in range(20):
            Patient.objects.create(distribution=distribution, number_designation=1 + i, COVID=not bool(i % 5),
                                   CCU=not bool(i % 3))

        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [16, 17, 17, 17]
        expected_assigned_CCU_censuses = [4, 4, 4, 5]
        expected_assigned_COVID_censuses = [3, 2, 3, 3]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])

    def test_can_assign_two_bounces_and_a_sick_small_distribution(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        expected_starting_total_censuses = [11, 13, 10, 11]
        expected_starting_CCU_censuses = [3, 2, 2, 1]
        expected_starting_COVID_censuses = [3, 1, 0, 2]
        actual_starting_total_censuses = [line_item.startingcensus.total_census for line_item in
                                          distribution.return_ordered_rounder_line_items()]
        self.assertEqual(expected_starting_total_censuses, actual_starting_total_censuses)
        self.assertEqual(expected_starting_CCU_censuses, [line_item.startingcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_starting_COVID_censuses, [line_item.startingcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        Patient.objects.create(distribution=distribution, number_designation=17, CCU=True,
                               bounce_to=Provider.objects.get(display_name='provA'))
        Patient.objects.create(distribution=distribution, number_designation=18, CCU=True, COVID=True,
                               bounce_to=Provider.objects.get(display_name='provC'))
        for i in range(5):
            Patient.objects.create(distribution=distribution, number_designation=1 + i, COVID=bool(i % 5),
                                   CCU=bool(i % 3))

        distribution.assign_all_seen_patients()
        expected_assigned_total_censuses = [12, 14, 13, 13]
        expected_assigned_CCU_censuses = [3, 3, 4, 3]
        expected_assigned_COVID_censuses = [3, 2, 2, 4]
        self.assertEqual(expected_assigned_total_censuses, [line_item.assignedcensus.total_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_CCU_censuses, [line_item.assignedcensus.CCU_census for line_item in
                                                          distribution.return_ordered_rounder_line_items()])
        self.assertEqual(expected_assigned_COVID_censuses, [line_item.assignedcensus.COVID_census for line_item in
                                                            distribution.return_ordered_rounder_line_items()])


class BugFixTests(TestCase):
    def test_2020_07_06_unassigned_patients_unexpectedly_appearing(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        qgenda_names = ['provA', 'provB', 'provC', 'provD', 'provE', 'provF', 'provG', 'provH', 'provI']
        totals = [12, 12, 12, 11, 11, 13, 11, 13, 12]
        CCUs = [2, 2, 0, 3, 1, 2, 2, 1, 0]
        COVIDs = [1, 0, 1, 1, 0, 1, 0, 0, 1]
        orders = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        for i in range(len(qgenda_names)):
            provider = Provider.objects.get_or_create(qgenda_name=qgenda_names[i])[0]
            rounder_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name=f'DOC{i}')
            line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
                distribution=distribution, provider=provider)
            line_item.rounder_role = rounder_role
            line_item.position_in_batting_order = orders[i]
            line_item.save()
            StartingCensus.objects.create(distribution_line_item=line_item, total_census=totals[i], CCU_census=CCUs[i],
                                          COVID_census=COVIDs[i])
        for i in range(14):
            if i + 1 == 7:
                bounce_to = Provider.objects.get(display_name='provD')
            else:
                bounce_to = None
            if i + 1 in [1, 10, 14]:
                CCU = True
            else:
                CCU = False
            if i + 1 in [11, 14]:
                COVID = True
            else:
                COVID = False
            Patient.objects.create(distribution=distribution, CCU=CCU, COVID=COVID, bounce_to=bounce_to,
                                   number_designation=i + 1)
        distribution.assign_all_seen_patients()
        expected_target_census_total_censuses = [13, 13, 13, 13, 13, 14, 14, 14, 14]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.allocatedcensus.total_census, expected_target_census_total_censuses[index])
        for patient in distribution.patients.all():
            self.assertIsNotNone(patient.distribution_line_item)

    def test_can_assign_all_CCU_pts(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(30):
            CCU = True
            Patient.objects.create(distribution=distribution, number_designation=i + 1, CCU=CCU)
        distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation < 24:
                self.assertIsNotNone(patient.distribution_line_item, f'{patient.number_designation}')
            else:
                self.assertIsNone(patient.distribution_line_item)

    def test_can_assign_all_COVID_pts(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(30):
            COVID = True
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID)
        distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation < 24:
                self.assertIsNotNone(patient.distribution_line_item, f'{patient.number_designation}')
            else:
                self.assertIsNone(patient.distribution_line_item)

    def test_can_assign_all_dual_pos_pts(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(30):
            COVID = True
            CCU = True
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU)
        distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation < 24:
                self.assertIsNotNone(patient.distribution_line_item, f'{patient.number_designation}')
            else:
                self.assertIsNone(patient.distribution_line_item)

    def test_can_assign_all_bounceback_pts(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(30):
            Patient.objects.create(distribution=distribution, number_designation=i + 1,
                                   bounce_to=Provider.objects.get(qgenda_name='provA'))
        distribution.assign_all_patients()
        for patient in distribution.patients.all():
             self.assertIsNotNone(patient.distribution_line_item, f'{patient.number_designation}')



class Assignnot_seenPatientsTests(TestCase):
    def create_distribution_with_pt_count_and_every_permutation_of_seen_COVID_bounce_and_CCU(self, pt_count):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(pt_count):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if (i // 4) % 2:
                bounce_to = Provider.objects.get(display_name='provA')
            else:
                bounce_to = None
            if (i // 8) % 2:
                not_seen = True
            else:
                not_seen = False
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=not_seen)

    def test_not_seen_patients_are_not_assigned_by_assign_all_seen_patients(self):
        self.create_distribution_with_pt_count_and_every_permutation_of_seen_COVID_bounce_and_CCU(pt_count=16)
        distribution = Distribution.objects.last()
        distribution.assign_all_seen_patients()
        for patient in Patient.objects.all():
            if patient.number_designation < 9:
                self.assertEqual(patient.not_seen, False)
            else:
                self.assertEqual(patient.not_seen, True)
            if patient.number_designation < 9:
                self.assertIsNotNone(
                    patient.distribution_line_item,
                    f"patient{patient.number_designation} COVID={patient.COVID} " + \
                    f"CCU={patient.CCU} not_seen={patient.not_seen}")
            else:
                self.assertIsNone(patient.distribution_line_item,
                                  f"patient{patient.number_designation} COVID={patient.COVID} " + \
                                  f"CCU={patient.CCU} not_seen={patient.not_seen}")

    def test_assign_not_seen_patients_assigns_not_seen_bounceback_patients_to_corresponding_provider(self):
        self.create_distribution_with_pt_count_and_every_permutation_of_seen_COVID_bounce_and_CCU(pt_count=16)
        distribution = Distribution.objects.last()
        self.assertEqual(
            Patient.objects.filter(not_seen=True, bounce_to__isnull=False, distribution_line_item__isnull=True).count(),
            4)
        distribution.assign_not_seen_patients()
        self.assertEqual(
            Patient.objects.filter(not_seen=True, bounce_to__isnull=False, distribution_line_item__isnull=True).count(),
            0)
        for patient in Patient.objects.filter(not_seen=True, bounce_to__isnull=False):
            self.assertIsNotNone(patient.distribution_line_item)
            self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')

    def test_single_non_bounce_not_seen_patient_goes_to_first_line_item_if_no_special_cases(self):
        # special cases include:  already got bouncebacks, additional pts would put over max censuses
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        Patient.objects.create(distribution=distribution, number_designation=1, not_seen=True, bounce_to=None)
        distribution.assign_not_seen_non_bounceback_patients()
        patient = Patient.objects.last()
        self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')

    def test_8_non_bounce_not_seen_patient_goes_to_successive_line_items_if_no_special_cases(self):
        # special cases include:  already got bouncebacks, additional pts would put over max censuses
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(8):
            Patient.objects.create(distribution=distribution, number_designation=i + 1, not_seen=True, bounce_to=None)
        distribution.assign_not_seen_non_bounceback_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [1, 5]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [2, 6]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [3, 5]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [4, 8]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')

    def test_8_non_bounce_not_seen_patient_distributed_to_successive_line_items_with_expected_priority(self):
        # expected priority is dual_pos patients, then CCU pos, then COVID pos, then dual_neg
        # therefore, should get assigned to line items 3 to B, 5 to C, 4 to A, 7 to D, 1 to B, 6 to C, 0 to A, 2 to D
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(8):
            if i in [3, 4, 5, 7]:
                CCU = True
            else:
                CCU = False
            if i in [1, 3, 5, 6]:
                COVID = True
            else:
                COVID = False
            Patient.objects.create(distribution=distribution, number_designation=i + 1, not_seen=True, bounce_to=None,
                                   CCU=CCU, COVID=COVID)
        distribution.assign_not_seen_non_bounceback_patients()
        # distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [2, 4]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [6, 7]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [1, 5]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [3, 8]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')

    def test_line_items_with_a_bounce_get_skipped_for_non_bounce_not_seen_patient_assignments(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(4):
            if i in [0]:
                bounce_to = Provider.objects.get(display_name='provA')
            elif i in [2]:
                bounce_to = Provider.objects.get(display_name='provB')
            else:
                bounce_to = None
            Patient.objects.create(distribution=distribution, number_designation=i + 1, not_seen=True,
                                   bounce_to=bounce_to)
        distribution.assign_not_seen_bounceback_patients()
        distribution.assign_not_seen_non_bounceback_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [3]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [2]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [1]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [4]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')

    def test_first_sixteen_non_bounce_not_seen_patients_assigned_to_line_items_in_expected_order(self):
        # expected order is bounces, then dual_pos assigned first, then COVID pos, then CCU pos, then dual neg
        # this should make A get num des 5-8, 13-16, then B gets 4, C gets 12, D gets 3, B gets 11, C gets 2, D gets 10,
        # and B gets 1, and C gets 9
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if (i // 4) % 2:
                bounce_to = Provider.objects.get(display_name='provA')
            else:
                bounce_to = None
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=True)
        distribution.assign_not_seen_patients()
        # distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [1, 4, 11]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [2, 9, 12]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [5, 6, 7, 8, 13, 14, 15, 16]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [3, 10]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')

    def test_confirming_distribution_order_for_error_in_functional_tests(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i in [2, 7, 11]:
                COVID = True
            else:
                COVID = False
            if i in [1, 2, 5, 6, 8, 11, 12]:
                CCU = True
            else:
                CCU = False
            if i in [0, 2, 5, 7, 10, 11, 14]:
                not_seen = True
            else:
                not_seen = False
            if i in [10]:
                bounce_to = Provider.objects.get(display_name='provC')
            elif i in [4]:
                bounce_to = Provider.objects.get(display_name='provA')
            else:
                bounce_to = None
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=not_seen)
        distribution.assign_all_patients()
        # unseen patients should be assigned by bouncebacks, dual pos, CCU pos, COVID pos, dual neg
        # therefore, 10 should go to C; then 2 to B, 11 to A; then 5 to D; then 7 to B; then
        # 0 to C, 14 to A
        for patient in distribution.patients.all():
            if patient.number_designation in [3, 8]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [1, 11]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [12, 15]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [6]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')

    def test_not_seen_patients_do_not_increase_the_numbers_of_assigned_patients(self):
        # expected order is bounces, then dual_pos assigned first, then COVID pos, then CCU pos, then dual neg
        # this should make A get num des 5-8, 13-16, then B gets 4, C gets 12, D gets 3, B gets 11, C gets 2, D gets 10,
        # and B gets 1, and C gets 9
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if (i // 4) % 2:
                bounce_to = Provider.objects.get(display_name='provA')
            else:
                bounce_to = None
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=True)
        distribution = Distribution.objects.last()
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_not_seen_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [1, 4, 11]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [2, 9, 12]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [5, 6, 7, 8, 13, 14, 15, 16]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [3, 10]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')
        starting_total_censuses = [11, 13, 10, 11]
        expected_assigned_totals = [11, 13, 10, 11]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.startingcensus.total_census, starting_total_censuses[index])
            self.assertEqual(line_item.assignedcensus.total_census, expected_assigned_totals[index])

    def test_assign_not_seen_patients_respects_total_maxima(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if i // 4:
                bounce_to = None
            else:
                bounce_to = Provider.objects.get(display_name='provA')
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=True)
        distribution = Distribution.objects.last()
        starting_census = [11, 13, 10, 11]
        arbitrary_total_maxima = [13, 20, 15, 12]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.startingcensus.total_census, starting_census[index])
            line_item.provider.max_total_census = arbitrary_total_maxima[index]
            line_item.provider.save()
        starting_census = [11, 13, 10, 11]
        #  expect 4 bouncebacks to go to A, 1-4(4 not_seen, bringing total to 14); then B gets 8(1u, t12),
        #  C gets 12(1u,t14), D gets 16(1U, t12 full) then B gets 7(2u, t13, full), C gets 11, 15, 6, 10(5u, t18),
        #  A gets 14(5u, t15), C gets 5 and 9(7u, t20, full)
        #   and 13 is unassigned
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_not_seen_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [7, 8]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [5, 6, 9, 10, 11, 12, 15]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [1, 2, 3, 4, 14]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [16]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')
            elif patient.number_designation in [13]:
                self.assertIsNone(patient.distribution_line_item)

    def test_assign_not_seen_patients_respects_CCU_maxima(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if i // 4:
                bounce_to = None
            else:
                bounce_to = Provider.objects.get(display_name='provA')
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=True)
        distribution = Distribution.objects.last()
        starting_CCU_census = [3, 2, 2, 1]
        arbitrary_CCU_maxima = [6, 3, 5, 1]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.startingcensus.CCU_census, starting_CCU_census[index])
            line_item.provider.max_CCU_census = arbitrary_CCU_maxima[index]
            line_item.provider.save()
        self.assertEqual(starting_CCU_census,
                         [line_item.startingcensus.CCU_census for line_item in
                          distribution.return_ordered_rounder_line_items()])
        #  expect 4 bouncebacks to go to A, 1-4(4 not_seen, bringing ccu total to 2+2=4); then B gets 8(1u, ccut 3+1=4),
        #  C gets 12(1u,ccut 2+1=3, full), B gets 16,7 (3U, ccut=6) then A gets 11 (5u, ccut=5, full)
        #  and 15 is unassigned
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_not_seen_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [7, 8, 16]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [12]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [3, 4, 11]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            # elif patient.number_designation in [16]:
            #     self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')
            elif patient.number_designation in [15]:
                self.assertIsNone(patient.distribution_line_item)

    def test_assign_not_seen_patients_respects_COVID_maxima(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(16):
            if i % 2:
                COVID = True
            else:
                COVID = False
            if (i // 2) % 2:
                CCU = True
            else:
                CCU = False
            if i // 4:
                bounce_to = None
            else:
                bounce_to = Provider.objects.get(display_name='provA')
            Patient.objects.create(distribution=distribution, number_designation=i + 1, COVID=COVID, CCU=CCU,
                                   bounce_to=bounce_to, not_seen=True)
        distribution = Distribution.objects.last()
        starting_COVID_census = [3, 1, 0, 2]
        arbitrary_COVID_maxima = [5, 2, 3, 3]
        for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
            self.assertEqual(line_item.startingcensus.COVID_census, starting_COVID_census[index])
            line_item.provider.max_COVID_census = arbitrary_COVID_maxima[index]
            line_item.provider.save()
        self.assertEqual(starting_COVID_census,
                         [line_item.startingcensus.COVID_census for line_item in
                          distribution.return_ordered_rounder_line_items()])
        #  expect 4 bouncebacks to go to A, 1-4(4 not_seen, bringing cov total to 0+2=2); then B gets 8(1u, covt 3+1=4),
        #  C gets 12(1u,covt 1+1=2, full), D gets 16 (1u, covt2+1=3, full), B gets 7 (2U, covt=4) then C gets 11 (2u),
        # then D gets 15(2u), then B gets 6(3u, covt=5, full), then A gets 10(3u, covt = 3, full) and
        #  and 14 is unassigned
        distribution.set_postbounce_allocated_assigned_censuses_to_start_census_and_unassign_any_prev_assigned_patients()
        distribution.assign_not_seen_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [6, 7, 8]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [11, 12]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [2, 4, 10]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            # elif patient.number_designation in [16]:
            #     self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')
            elif patient.number_designation in [14]:
                self.assertIsNone(patient.distribution_line_item)

    def test_assign_all_patients_fxn_assigns_motley_patients_as_expected(self):
        # expected order is bounces, then dual_pos assigned first, then COVID pos, then CCU pos, then dual neg
        self.create_distribution_with_pt_count_and_every_permutation_of_seen_COVID_bounce_and_CCU(16)
        distribution = Distribution.objects.last()
        distribution.assign_all_patients()
        for patient in distribution.patients.all():
            if patient.number_designation in [1, 3, 9, 12]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provB')
            elif patient.number_designation in [11]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provC')
            elif patient.number_designation in [5, 6, 7, 8, 13, 14, 15, 16]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provA')
            elif patient.number_designation in [2, 4, 10]:
                self.assertEqual(patient.distribution_line_item.provider.qgenda_name, 'provD')
