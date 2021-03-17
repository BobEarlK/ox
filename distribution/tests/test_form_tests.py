from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import reverse
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from ..forms import RounderStartingCensusForm, BaseStartingCensusFormset, PatientCountForm, PatientCharacteristicsForm, \
    BasePatientCharacteristicsFormset, ProviderUpdateForm, AddRounderFromExistingProvidersForm, AddNewRounderForm, \
    EmailDistributionForm
from ..helper_fxns import helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items, \
    helper_fxn_add_4_non_rounder_line_items_to_distribution
from ..mock_qgenda_data import mock_qgenda_relevant_data
from ..models import StartingCensus, Distribution, Provider, DistributionLineItem, Patient, Role, EmailAddressee, \
    DistributionEmail


class RounderStartingCensusFormTests(TestCase):
    def test_can_create_form(self):
        form = RounderStartingCensusForm()
        self.assertIsInstance(form, RounderStartingCensusForm)

    def test_saving_form_creates_starting_census_and_assigns_it_to_line_item(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': '1', 'total_census': '12', 'CCU_census': '3', 'COVID_census': '2'}
        form = RounderStartingCensusForm(data=data)
        if form.is_valid():
            saved_form_object = form.save()
        self.assertEqual(saved_form_object, StartingCensus.objects.get(pk=1))

    def test_saving_form_where_starting_data_overwrites_line_item_starting_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': '1', 'total_census': '12', 'CCU_census': '3', 'COVID_census': '2'}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(distribution.line_items.count(), 1)
        self.assertEqual(StartingCensus.objects.count(), 0)
        with self.assertRaises(ObjectDoesNotExist):
            starting_census = distribution.line_items.first().startingcensus
        form.save()
        self.assertEqual(distribution.line_items.count(), 1)
        self.assertEqual(StartingCensus.objects.count(), 1)
        self.assertIsNotNone(distribution.line_items.first().startingcensus)
        self.assertEqual(distribution.line_items.first().startingcensus.total_census, 12)
        self.assertEqual(distribution.line_items.first().startingcensus.CCU_census, 3)
        self.assertEqual(distribution.line_items.first().startingcensus.COVID_census, 2)
        data = {'distribution_line_item': 1, 'total_census': 10, 'CCU_census': 5, 'COVID_census': 6}
        form = RounderStartingCensusForm(data=data)
        print(form.errors)
        if form.is_valid():
            pass
        self.assertEqual(distribution.line_items.count(), 1)
        self.assertEqual(StartingCensus.objects.count(), 1)
        form.save()
        self.assertIsNotNone(distribution.line_items.first().startingcensus)
        self.assertEqual(distribution.line_items.count(), 1)
        self.assertEqual(StartingCensus.objects.count(), 1)
        self.assertEqual(distribution.line_items.first().startingcensus.total_census, 10)
        self.assertEqual(distribution.line_items.first().startingcensus.CCU_census, 5)
        self.assertEqual(distribution.line_items.first().startingcensus.COVID_census, 6)

    def test_form_without_total_census_is_not_valid(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': '1', 'total_census': '', 'CCU_census': '3', 'COVID_census': '2'}
        form = RounderStartingCensusForm(data=data)
        self.assertFalse(form.is_valid())

    def test_saving_form_with_total_census_assigns_that_number_to_line_item_starting_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': '1', 'total_census': '12', 'CCU_census': '3', 'COVID_census': '2'}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(line_item.startingcensus.total_census, 12)

    def test_form_without_CCU_census_is_valid_and_assigns_zero(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': 1, 'total_census': 12, 'CCU_census': '', 'COVID_census': 2}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(line_item.startingcensus.CCU_census, 0)

    def test_saving_form_with_CCU_census_assigns_that_number_to_line_item_starting_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': 1, 'total_census': 12, 'CCU_census': 3, 'COVID_census': 2}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(line_item.startingcensus.CCU_census, 3)

    def test_form_without_COVID_census_is_valid_and_assigns_zero(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': 1, 'total_census': 12, 'CCU_census': 3, 'COVID_census': ''}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(line_item.startingcensus.COVID_census, 0)

    def test_saving_form_with_COVID_census_assigns_that_number_to_line_item_starting_census(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        provider = Provider.objects.get_or_create_from_qgenda_name(qgenda_name='provA')
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(
            distribution=distribution, provider=provider)
        data = {'distribution_line_item': 1, 'total_census': 12, 'CCU_census': 3, 'COVID_census': 2}
        form = RounderStartingCensusForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(line_item.startingcensus.COVID_census, 2)


class StartingCensusFormsetTests(TestCase):
    def test_can_create_formset(self):
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        formset = StartingCensusFormset()
        self.assertIsInstance(formset, StartingCensusFormset)

    def test_creating_formset_creates_form_for_each_line_item_in_distribution(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution))
        self.assertEqual(len(starting_census_formset), 9)
        for form in starting_census_formset.forms:
            self.assertIsInstance(form, RounderStartingCensusForm)

    def test_formset_ordered_by_position_in_batting_order(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        expected_order = ['provB', 'provC', 'provA', 'provD']
        self.assertEqual(
            [line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
            expected_order)
        self.assertEqual(
            [form.instance.distribution_line_item.provider.display_name for form in starting_census_formset.forms],
            expected_order)
        distribution.move_line_item_to_next_up(distribution.line_items.get(provider__display_name='provD'))
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        expected_order = ['provD', 'provB', 'provC', 'provA']
        self.assertEqual(
            [line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
            expected_order)
        self.assertEqual(
            [form.instance.distribution_line_item.provider.display_name for form in starting_census_formset.forms],
            expected_order)

    def test_formset_contains_crispy_form_helper_elements_in_expected_order(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        for form in starting_census_formset.forms:
            form_rounder_fields = form.helper.layout[0][0].fields
            form_census_fields = form.helper.layout[0][1].fields
            self.assertEqual(len(form_rounder_fields), 5)
            self.assertEqual(len(form_census_fields), 3)
            self.assertIn('''id="id_next_up_link''', form_rounder_fields[0].html)
            self.assertEqual('id', form_rounder_fields[1].fields[0])
            self.assertEqual('distribution_line_item', form_rounder_fields[2].fields[0])
            for text in ['''id="id_rounder_cell"''', '''id="id_rounder_text"''']:
                self.assertIn(text, form_rounder_fields[3].html)
            self.assertIn('''id="id_rounder_supplemental_text''', form_rounder_fields[4].html)
            self.assertEqual('total_census', form_census_fields[0].fields[0])
            self.assertEqual('CCU_census', form_census_fields[1].fields[0])
            self.assertEqual('COVID_census', form_census_fields[2].fields[0])

    def test_formset_contains_link_to_update_provider_in_crispy_forms_helper(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        for index, form in enumerate(starting_census_formset.forms):
            form_rounder_fields = form.helper.layout[0][0].fields
            rounder_html = form_rounder_fields[3].html
            self.assertIn(f'''href="{{% url 'distribution:update_provider' provider_qgenda_name=''' + \
                          f"'{form.instance.distribution_line_item.provider.qgenda_name}'" + "%}", rounder_html)

    def test_formset_contains_triage_text_in_crispy_forms_helper_if_am_triage_or_pm_triage(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        am_triage_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='AM TRIAGE')
        pm_triage_role = Role.objects.get_or_create_from_qgenda_name(qgenda_name='PM TRIAGE')
        distribution.return_ordered_rounder_line_items()[0].assign_role(
            am_triage_role)  # should be 'provB' in the 1st form
        distribution.return_ordered_rounder_line_items()[2].assign_role(
            pm_triage_role)  # should be 'provA' in the 3rd form
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        for index, form in enumerate(starting_census_formset.forms):
            form_rounder_fields = form.helper.layout[0][0].fields
            supplemental_html = form_rounder_fields[4].html
            if index == 0:
                self.assertIn('''<span class="am-triage">a.m. triage</span>''', supplemental_html)
            elif index == 2:
                self.assertIn('''<span class="pm-triage">p.m. triage</span>''', supplemental_html)
            else:
                self.assertEqual(
                    supplemental_html,
                    f'''<p id="id_rounder_supplemental_text" class="rounder-supplemental-text"></p></div>''')

    def test_formset_contains_maxima_in_crispy_forms_helper_if_other_than_default_maxima(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        distribution.return_ordered_rounder_line_items()[1].provider.set_max_censuses_to_census_track(
            'teaching')  # should be 'provC' in the 2nd form
        distribution.return_ordered_rounder_line_items()[3].provider.set_max_censuses_to_census_track(
            'COVID-free')  # should be 'provD' in the 4th form
        custom_provider = distribution.return_ordered_rounder_line_items()[0].provider
        custom_provider.max_total_census, custom_provider.max_CCU_census, custom_provider.max_COVID_census = 11, 5, 1
        custom_provider.save()
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
        for index, form in enumerate(starting_census_formset.forms):
            form_rounder_fields = form.helper.layout[0][0].fields
            supplemental_html = form_rounder_fields[4].html
            if index in [0, 1]:
                self.assertIn('''<span class="custom-max-total-census">''', supplemental_html)
                self.assertIn('''<span class="custom-max-CCU-census">''', supplemental_html)
            else:
                self.assertNotIn('''<span class="custom-max-total-census">''', supplemental_html)
                self.assertNotIn('''<span class="custom-max-CCU-census">''', supplemental_html)
            if index in [0, 1, 3]:
                self.assertIn('''<span class="custom-max-COVID-census">''', supplemental_html)
            else:
                self.assertNotIn('''<span class="custom-max-COVID-census">''', supplemental_html)

    def test_saving_formset_updates_starting_censuses_for_line_items(self):
        distribution = Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
            date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        self.assertEqual(StartingCensus.objects.count(), 9)
        for starting_census in StartingCensus.objects.all():
            self.assertEqual(starting_census.total_census, None)
            self.assertEqual(starting_census.CCU_census, None)
            self.assertEqual(starting_census.COVID_census, None)
        data = {'form-TOTAL_FORMS': 9, 'form-INITIAL_FORMS': 9}
        ordered_rounder_line_items = distribution.return_ordered_rounder_line_items()
        starting_totals = [11, 12, 14, 15, 9, 8, 16, 13, 14]
        starting_CCUs = [2, 5, 3, 7, 0, 1, 0, 1, 0]
        starting_COVIDs = [1, 2, 0, 0, 3, 0, 4, 3, 7]
        for i in range(9):
            data.update({f'form-{i}-id': i + 1})
            data.update({f'form-{i}-distribution_line_item': ordered_rounder_line_items[i].id})
            data.update({f'form-{i}-total_census': starting_totals[i]})
            data.update({f'form-{i}-CCU_census': starting_CCUs[i]})
            data.update({f'form-{i}-COVID_census': starting_COVIDs[i]})
        StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                           formset=BaseStartingCensusFormset,
                                                           model=StartingCensus)
        starting_census_formset = StartingCensusFormset(data=data,
                                                        queryset=StartingCensus.objects.filter(
                                                            distribution_line_item__distribution=distribution))
        self.assertTrue(starting_census_formset.is_valid())
        starting_census_formset.save()
        for index, starting_census in enumerate(line_item.startingcensus for line_item in ordered_rounder_line_items):
            self.assertEqual(starting_census.total_census, starting_totals[index])
            self.assertEqual(starting_census.CCU_census, starting_CCUs[index])
            self.assertEqual(starting_census.COVID_census, starting_COVIDs[index])


class AddRounderFromExistingProvidersFormTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        # create_some_providers_who_are_not_current_rounders
        Provider.objects.create(qgenda_name='AnotherProvider')
        Provider.objects.create(qgenda_name='YetAnotherProvider')

    def test_can_create_form(self):
        distribution = Distribution.objects.last()
        form = AddRounderFromExistingProvidersForm(distribution=distribution)
        self.assertIsInstance(form, AddRounderFromExistingProvidersForm)

    def test_saving_form_creates_new_rounder_line_item_in_last_position_of_batting_order(self):
        distribution = Distribution.objects.last()
        data = {'provider': Provider.objects.get(qgenda_name='AnotherProvider')}
        form = AddRounderFromExistingProvidersForm(data=data, distribution=distribution)
        self.assertTrue(form.is_valid())
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        form.save()
        self.assertIsInstance(form.instance, DistributionLineItem)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.display_name,
                         'AnotherProvider')
        data = {'provider': Provider.objects.get(qgenda_name='YetAnotherProvider')}
        form = AddRounderFromExistingProvidersForm(data=data, distribution=distribution)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertIsInstance(form.instance, DistributionLineItem)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 6)
        self.assertEqual(
            [line_item.provider.display_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provC', 'provA', 'provD', 'AnotherProvider', 'YetAnotherProvider'])

    def test_form_choices_include_providers_in_database(self):
        distribution = Distribution.objects.last()
        form = AddRounderFromExistingProvidersForm(distribution=distribution)
        self.assertEqual(form.fields['provider'].queryset.count(), 4)
        for provider in Provider.objects.filter(qgenda_name__endswith='AnotherProvider'):
            self.assertIn(provider, form.fields['provider'].queryset)

    def test_form_choices_exclude_providers_in_database(self):
        distribution = Distribution.objects.last()
        form = AddRounderFromExistingProvidersForm(distribution=distribution)
        for provider in Provider.objects.filter(qgenda_name__in=['provA', 'provB', 'provC', 'provD']):
            self.assertNotIn(provider, form.fields['provider'].queryset)


class AddNewRounderFormTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()

    def test_can_create_form(self):
        distribution = Distribution.objects.last()
        form = AddNewRounderForm(distribution=distribution)
        self.assertIsInstance(form, AddNewRounderForm)

    def test_saving_form_creates_new_rounder_line_item_in_last_position_of_batting_order(self):
        distribution = Distribution.objects.last()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        data = {'input_name': 'NewBy'}
        form = AddNewRounderForm(distribution=distribution, data=data)
        form.full_clean()
        if form.is_valid():
            form.save()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.display_name, '_NewBy')
        self.assertIsInstance(form, AddNewRounderForm)

    def test_trying_to_save_form_with_name_already_in_db_but_not_already_in_rounders_adds_existing_rounder(self):
        # this catches prevents a user recreating a provider
        distribution = Distribution.objects.last()
        Provider.objects.create(qgenda_name='provQ')
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.assertEqual(len([line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]), 4)
        data = {'input_name': 'provQ'}
        form = AddNewRounderForm(distribution=distribution, data=data)
        form.full_clean()
        if form.is_valid():
            form.save()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(len([line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]), 5)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.display_name, 'provQ')

    def test_trying_to_save_form_with_name_already_in_db_and_among_rounders_does_nothing(self):
        # this catches prevents a user recreating a provider
        distribution = Distribution.objects.last()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.assertEqual(len([line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]), 4)
        data = {'input_name': 'provA'}
        form = AddNewRounderForm(distribution=distribution, data=data)
        form.full_clean()
        if form.is_valid():
            form.save()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.assertEqual(len([line_item.provider for line_item in distribution.return_ordered_rounder_line_items()]), 4)


class PatientCountFormTests(TestCase):
    def test_can_create_form(self):
        form = PatientCountForm()
        self.assertIsInstance(form, PatientCountForm)

    def test_saving_form_assigns_patient_count_to_distribution(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        data = {'count_to_distribute': 14}
        form = PatientCountForm(data=data, instance=distribution)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(Distribution.objects.first().count_to_distribute, 14)

    def test_saving_form_creates_that_number_of_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        data = {'count_to_distribute': 14}
        form = PatientCountForm(data=data, instance=distribution)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 14)
        for patient in Patient.objects.all():
            self.assertTrue(patient.distribution == distribution)

    def test_saving_form_deletes_any_previously_assigned_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        data = {'count_to_distribute': 14}
        form = PatientCountForm(data=data, instance=distribution)
        self.assertTrue(form.is_valid())
        form.save()
        data = {'count_to_distribute': 8}
        form = PatientCountForm(data=data, instance=distribution)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 8)
        for patient in Patient.objects.all():
            self.assertTrue(patient.distribution == distribution)


class PatientCharacteristicsFormTest(TestCase):
    def test_can_create_form(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        patient = Patient.objects.create(distribution=distribution, number_designation=1)
        form = PatientCharacteristicsForm(instance=patient)
        self.assertIsInstance(form, PatientCharacteristicsForm)

    def test_form_bounce_to_options_are_todays_rounders(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        patient = Patient.objects.create(distribution=distribution, number_designation=1)
        form = PatientCharacteristicsForm(instance=patient)
        self.assertEqual([choice[1] for choice in form.fields['bounce_to'].choices],
                         ['', 'provA', 'provB', 'provC', 'provD'])

    def test_form_bounce_to_options_do_not_include_non_rounder_providers(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        helper_fxn_add_4_non_rounder_line_items_to_distribution(distribution=distribution)
        patient = Patient.objects.create(distribution=distribution, number_designation=1)
        form = PatientCharacteristicsForm(instance=patient)
        self.assertEqual([choice[1] for choice in form.fields['bounce_to'].choices],
                         ['', 'provA', 'provB', 'provC', 'provD'])

    def test_saving_form_updates_patient(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        patient = Patient.objects.create(distribution=distribution, number_designation=1)
        data = {'CCU': True, 'COVID': True, 'number_designation': 1, 'bounce_to': 'provA', 'not_seen': True}
        form = PatientCharacteristicsForm(instance=patient, data=data)
        form.full_clean()
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Patient.objects.count(), 1)
        patient = Patient.objects.first()
        self.assertEqual(patient.CCU, True)
        self.assertEqual(patient.COVID, True)
        self.assertEqual(patient.bounce_to, Provider.objects.get(display_name='provA'))
        self.assertEqual(patient.not_seen, True)


class PatientCharacteristicsFormsetTests(TestCase):
    def test_can_create_formset(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                                   fields=['CCU', 'COVID', 'not_seen',
                                                                           'bounce_to'],
                                                                   formset=BasePatientCharacteristicsFormset)
        formset = PatientCharacteristicsFormset(distribution_id=1)
        self.assertIsInstance(formset, PatientCharacteristicsFormset)

    def test_newly_created_formset_forms_have_instances_of_patients_from_the_given_distribution(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                                   fields=['CCU', 'COVID', 'not_seen',
                                                                           'bounce_to'],
                                                                   formset=BasePatientCharacteristicsFormset)
        formset = PatientCharacteristicsFormset(distribution_id=1)
        self.assertEqual(len(formset.forms), 0)
        for i in range(6):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
        formset = PatientCharacteristicsFormset(distribution_id=1)
        self.assertEqual(len(formset.forms), 6)

    def test_newly_created_formset_forms_have_bounceback_choices_from_current_distribution_providers(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                                   fields=['CCU', 'COVID', 'not_seen',
                                                                           'bounce_to'],
                                                                   formset=BasePatientCharacteristicsFormset)
        for i in range(6):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
        formset = PatientCharacteristicsFormset(distribution_id=1)
        for form in formset.forms:
            form.fields['bounce_to'].queryset = Provider.objects.filter(
                line_items__in=distribution.return_ordered_rounder_line_items())

    def test_saving_formset_data_with_previously_created_patients_updates_the_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        for i in range(4):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
            data = {
                'form-TOTAL_FORMS': 4,
                'form-INITIAL_FORMS': 4,
                'form-0-distribution': 1,
                'form-1-distribution': 1,
                'form-2-distribution': 1,
                'form-3-distribution': 1,
                'form-0-id': 1,
                'form-1-id': 2,
                'form-2-id': 3,
                'form-3-id': 4,
                'form-0-COVID': True,
                'form-3-CCU': True,
                'form-1-not_seen': True,
                'form-2-not_seen': True,
            }
        PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                                   fields=['CCU', 'COVID', 'not_seen', 'bounce_to'],
                                                                   formset=BasePatientCharacteristicsFormset)
        formset = PatientCharacteristicsFormset(distribution_id=distribution.id, data=data)
        formset.full_clean()
        self.assertTrue(formset.is_valid())
        formset.save()
        self.assertEqual(Patient.objects.count(), 4)
        for patient in Patient.objects.all():
            if patient.id == 1:
                self.assertEqual(patient.COVID, True)
            else:
                self.assertEqual(patient.COVID, False)
            if patient.id == 4:
                self.assertEqual(patient.CCU, True)
            else:
                self.assertEqual(patient.CCU, False)
            if patient.id in [2, 3]:
                self.assertEqual(patient.not_seen, True)
            else:
                self.assertEqual(patient.not_seen, False)

    def test_saving_formset_data_with_real_actual_data_updates_the_patients(self):
        distribution = Distribution.objects.create(date=timezone.localdate())
        data = {'csrfmiddlewaretoken': ['ekWtCWSSHT499JCSUzOBFKiFD3y6eneLtDzkjAvV1kyuIw8A2mEUE8m5OruEabgG'],
                'form-TOTAL_FORMS': 31, 'form-INITIAL_FORMS': 31, 'form-0-id': ['1'], 'form-0-CCU': ['on'],
                'form-0-bounce_to': [''],
                'form-1-id': ['2'], 'form-1-bounce_to': [''], 'form-2-id': ['3'], 'form-2-bounce_to': [''],
                'form-3-id': ['4'], 'form-3-COVID': ['on'], 'form-3-bounce_to': [''], 'form-4-id': ['5'],
                'form-4-bounce_to': [''], 'form-5-id': ['6'], 'form-5-bounce_to': [''], 'form-6-id': ['7'],
                'form-6-bounce_to': [''], 'form-7-id': ['8'], 'form-7-bounce_to': [''],
                'form-8-id': ['9'], 'form-8-bounce_to': [''], 'form-9-id': ['10'], 'form-9-bounce_to': [''],
                'form-10-id': ['11'], 'form-10-bounce_to': [''], 'form-11-id': ['12'], 'form-11-bounce_to': [''],
                'form-12-id': ['13'], 'form-12-bounce_to': [''], 'form-13-id': ['14'], 'form-13-bounce_to': [''],
                'form-14-id': ['15'], 'form-14-bounce_to': [''], 'form-15-id': ['16'], 'form-15-bounce_to': [''],
                'form-16-id': ['17'], 'form-16-bounce_to': [''], 'form-17-id': ['18'], 'form-17-bounce_to': [''],
                'form-18-id': ['19'], 'form-18-bounce_to': [''], 'form-19-id': ['20'], 'form-19-bounce_to': [''],
                'form-20-id': ['21'], 'form-20-bounce_to': [''], 'form-21-id': ['22'], 'form-21-bounce_to': [''],
                'form-22-id': ['23'], 'form-22-bounce_to': [''], 'form-23-id': ['24'], 'form-23-bounce_to': [''],
                'form-24-id': ['25'], 'form-24-bounce_to': [''], 'form-25-id': ['26'], 'form-25-bounce_to': [''],
                'form-26-id': ['27'], 'form-26-bounce_to': [''], 'form-27-id': ['28'], 'form-27-bounce_to': [''],
                'form-28-id': ['29'], 'form-28-bounce_to': [''], 'form-29-id': ['30'], 'form-29-bounce_to': [''],
                'form-30-id': ['31'], 'form-30-bounce_to': [''], 'submit_patient_forms': ['Submit']}
        data = {}
        for i in range(31):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
            data.update({'form-TOTAL_FORMS': i + 1, 'form-INITIAL_FORMS': i + 1, f'form-{i}-distribution': i + 1,
                         f'form-{i}-id': i + 1, f'form-{i}-COVID': False, f'form-{i}-CCU': False,
                         f'form-{i}-not_seen': True})
        PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                                   fields=['CCU', 'COVID', 'not_seen', 'bounce_to'],
                                                                   formset=BasePatientCharacteristicsFormset)
        formset = PatientCharacteristicsFormset(distribution_id=distribution.id, data=data)
        formset.full_clean()
        self.assertTrue(formset.is_valid())
        formset.save()

class ProviderUpdateFormTests(TestCase):
    def test_can_create_form(self):
        provider = Provider.objects.create()
        form = ProviderUpdateForm(instance=provider)
        self.assertIsInstance(form, ProviderUpdateForm)

    def test_form_displays_existing_values_for_display_name_and_max_values(self):
        provider = Provider.objects.create(qgenda_name='provA')
        form = ProviderUpdateForm(instance=provider)
        self.assertEqual(form.initial['display_name'], 'provA')
        self.assertEqual(form.initial['max_total_census'], 17)
        self.assertEqual(form.initial['max_CCU_census'], 17)
        self.assertEqual(form.initial['max_COVID_census'], 17)

    def test_saving_form_changes_instance_values(self):
        provider = Provider.objects.create(qgenda_name='provA')
        data = {'display_name': 'Iggy', 'max_total_census': 14, 'max_CCU_census': 5, 'max_COVID_census': 3}
        form = ProviderUpdateForm(instance=provider, data=data)
        if not form.is_valid():
            self.fail('invalid form')
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.display_name, 'provA')
        self.assertEqual(provider.max_total_census, 17)
        self.assertEqual(provider.max_CCU_census, 17)
        self.assertEqual(provider.max_COVID_census, 17)
        form.save()
        provider = Provider.objects.first()
        self.assertEqual(provider.display_name, 'Iggy')
        self.assertEqual(provider.max_total_census, 14)
        self.assertEqual(provider.max_CCU_census, 5)
        self.assertEqual(provider.max_COVID_census, 3)


class EMailFormTests(TestCase):
    def test_can_make_email_form(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_form = EmailDistributionForm(distribution=distribution)
        self.assertIsInstance(email_form, EmailDistributionForm)

    def test_form_has_pre_filled_subject(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_form = EmailDistributionForm(distribution=distribution)
        self.assertEqual(email_form.initial['subject'],
                         f'Pt Assignment - {distribution.date.strftime("%a   %m/%d/%y")}')

    def test_form_has_choose_recipient_field(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_form = EmailDistributionForm(distribution=distribution)
        self.assertEqual(email_form.fields['recipient_choices'].queryset.count(), 5)

    def test_form_can_choose_recipients_with_intensivist_and_id_emails(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_addressee_start_values = [('Hospitalists', 'test@test.com', True, True),
                                        ('Cheryl', 'test@test.com', True, True),
                                        ('Susan', 'test@test.com', True, True),
                                        ('Intensivists', 'test@test.com', True, False),
                                        ('ID docs', 'test@test.com', True, False)]

        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        email_form = EmailDistributionForm(distribution=distribution)
        for addressee in EmailAddressee.objects.all():
            self.assertIn(addressee, email_form.fields['recipient_choices'].queryset)

    def test_form_has_pre_chosen_hospitalists_as_recipients(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_addressee_start_values = [('Hospitalists', 'test@test.com', True, True),
                                        ('Cheryl', 'test@test.com', True, True),
                                        ('Susan', 'test@test.com', True, True),
                                        ('Intensivists', 'test@test.com', True, False),
                                        ('ID docs', 'test@test.com', True, False)]

        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        email_form = EmailDistributionForm(distribution=distribution)
        for addressee in EmailAddressee.objects.filter(pre_checked=True):
            self.assertIn(addressee, email_form.initial['recipient_choices'])
        for addressee in EmailAddressee.objects.filter(pre_checked=False):
            self.assertNotIn(addressee, email_form.initial['recipient_choices'])


class MoreEMailFormTests(TestCase):
    def test_saving_form_creates_email_with_selected_recipients_in_recipient_list(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        EmailAddressee.objects.all().delete()
        email_addressee_start_values = [('Hospitalists', 'test@test.com', True, True),
                                        ('Cheryl', 'test@test.com', True, True),
                                        ('Susan', 'test@test.com', True, True),
                                        ('Intensivists', 'test@test.com', True, False),
                                        ('ID docs', 'test@test.com', True, False)]
        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        data = {'subject': 'test subject', 'recipient_choices': ['1', '3', '5']}
        email_form = EmailDistributionForm(distribution=distribution, data=data)
        self.assertEqual(DistributionEmail.objects.count(), 0)
        email_form.save()
        self.assertEqual(DistributionEmail.objects.count(), 1)
        for email_addressee in EmailAddressee.objects.all():
            self.assertIn(email_addressee.email_address, DistributionEmail.objects.last().recipient_text_field)

class YetMoreEMailFormTests(TestCase):
    def test_saving_form_creates_email_with_subject_and_html_message_populated(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        email_addressee_start_values = [('Hospitalists', 'test@test.com', True, True),
                                        ('Cheryl', 'test@test.com', True, True),
                                        ('Susan', 'test@test.com', True, True),
                                        ('Intensivists', 'test@test.com', True, False),
                                        ('ID docs', 'test@test.com', True, False)]
        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        data = {'subject': 'test subject', 'recipient_choices': ['1', '3', '5']}
        email_form = EmailDistributionForm(distribution=distribution, data=data)
        email_form.save()
        self.assertEqual(DistributionEmail.objects.count(), 1)
        self.assertEqual('test subject', DistributionEmail.objects.last().subject)
        self.assertIn("<html>", DistributionEmail.objects.last().html_message)
