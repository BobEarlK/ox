import mock
from django.core import mail
from django.test import TestCase
from django.urls import reverse, resolve
from django.utils import timezone

from ..forms import PatientCountForm, ProviderUpdateForm, AddRounderFromExistingProvidersForm, AddNewRounderForm, \
    EmailDistributionForm
from ..helper_fxns import helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items, \
    helper_fxn_add_4_non_rounder_line_items_to_distribution
from ..mock_qgenda_data import mock_qgenda_relevant_data
from ..models import Distribution, DistributionManager, Provider, DistributionLineItem, Role, Patient, EmailAddressee, \
    DistributionEmail


class CurrentRoundersViewTests(TestCase):
    def test_view_resolves_url(self):
        url = '/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:current_rounders')

    def test_view_gets_success_status_code(self):
        url = reverse('distribution:current_rounders')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = reverse('distribution:current_rounders', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = reverse('distribution:current_rounders')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/current_rounders.html')

    def test_view_creates_distribution_from_qgenda_data_if_none_prior_for_date(self):
        url = reverse('distribution:current_rounders')
        self.assertEqual(Distribution.objects.count(), 0)
        response = self.client.get(url)
        self.assertEqual(Distribution.objects.count(), 1)
        response = self.client.get(url)
        self.assertEqual(Distribution.objects.count(), 1)

    def test_view_contains_rounder_formset_with_rounder_forms_in_expected_order(self):
        mock_distribution = \
            Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
                date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        with mock.patch.object(DistributionManager, 'get_last_for_date_or_create_new', return_value=mock_distribution):
            url = reverse('distribution:current_rounders')
            response = self.client.get(url)
            self.assertEqual(Distribution.objects.count(), 1)
            distribution = Distribution.objects.first()
            self.assertEqual(distribution.line_items.count(), 16)
            self.assertEqual(len(response.context['starting_census_formset']), 9)
            self.assertEqual('DOC1',
                             response.context['starting_census_formset'][
                                 0].instance.distribution_line_item.rounder_role.qgenda_name)
            self.assertEqual('DOC7',
                             response.context['starting_census_formset'][
                                 6].instance.distribution_line_item.rounder_role.qgenda_name)

    def test_view_displays_last_distribution_from_today_if_one_exists(self):
        provider = Provider.objects.create(display_name='provA')
        distribution = Distribution.objects.create(date=timezone.localdate())
        line_item = DistributionLineItem.objects.get_or_create_from_distribution_and_provider(distribution=distribution,
                                                                                              provider=provider)
        line_item.rounder_role = Role.objects.get_or_create_from_qgenda_name('DOC4')
        line_item.save()
        distribution.create_blank_starting_census_for_each_rounding_line_item()
        url = reverse('distribution:current_rounders')
        response = self.client.get(url)
        self.assertEqual(Distribution.objects.count(), 1)
        distribution = Distribution.objects.first()
        self.assertEqual(distribution.line_items.count(), 1)
        self.assertEqual(len(response.context['starting_census_formset']), 1)
        self.assertEqual(
            response.context['starting_census_formset'][0].instance.distribution_line_item.rounder_role.qgenda_name,
            'DOC4')

    def test_posting_valid_data_to_view_saves_starting_census_data(self):
        mock_distribution = \
            Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
                date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        with mock.patch.object(DistributionManager, 'get_last_for_date_or_create_new', return_value=mock_distribution):
            url = reverse('distribution:current_rounders')
            self.client.get(url)
            distribution = Distribution.objects.first()
            ordered_rounder_line_items = distribution.return_ordered_rounder_line_items()
            data = {'form-TOTAL_FORMS': 9, 'form-INITIAL_FORMS': 9}
            starting_totals = [11, 12, 14, 15, 9, 8, 16, 13, 14]
            starting_CCUs = [2, 5, 3, 7, 0, 1, 0, 1, 0]
            starting_COVIDs = [1, 2, 0, 0, 3, 0, 4, 3, 7]
            for i in range(9):
                data.update({f'form-{i}-id': i + 1})
                data.update({f'form-{i}-distribution_line_item': ordered_rounder_line_items[i].id})
                data.update({f'form-{i}-total_census': starting_totals[i]})
                data.update({f'form-{i}-CCU_census': starting_CCUs[i]})
                data.update({f'form-{i}-COVID_census': starting_COVIDs[i]})
            self.client.post(url, data=data)
            for index, line_item in enumerate(distribution.return_ordered_rounder_line_items()):
                self.assertIsNotNone(line_item.startingcensus)
                self.assertEqual(line_item.startingcensus.total_census, starting_totals[index])
                self.assertEqual(line_item.startingcensus.CCU_census, starting_CCUs[index])
                self.assertEqual(line_item.startingcensus.COVID_census, starting_COVIDs[index])

    def test_posting_valid_data_to_view_redirects_to_patient_count_view(self):
        mock_distribution = \
            Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
                date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        with mock.patch.object(DistributionManager, 'get_last_for_date_or_create_new', return_value=mock_distribution):
            url = reverse('distribution:current_rounders')
            response = self.client.get(url)
            distribution = Distribution.objects.first()
            ordered_rounder_line_items = distribution.return_ordered_rounder_line_items()
            data = {'form-TOTAL_FORMS': 9, 'form-INITIAL_FORMS': 9}
            starting_totals = [11, 12, 14, 15, 9, 8, 16, 13, 14]
            starting_CCUs = [2, 5, 3, 7, 0, 1, 0, 1, 0]
            starting_COVIDs = [1, 2, 0, 0, 3, 0, 4, 3, 7]
            for i in range(9):
                data.update({f'form-{i}-id': i + 1})
                data.update({f'form-{i}-distribution_line_item': ordered_rounder_line_items[i].id})
                data.update({f'form-{i}-total_census': starting_totals[i]})
                data.update({f'form-{i}-CCU_census': starting_CCUs[i]})
                data.update({f'form-{i}-COVID_census': starting_COVIDs[i]})
            response = self.client.post(url, data=data)
            self.assertRedirects(response, reverse('distribution:patient_count',
                                                   kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_posting_invalid_data_to_view_stays_on_view(self):
        mock_distribution = \
            Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
                date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        with mock.patch.object(DistributionManager, 'get_last_for_date_or_create_new', return_value=mock_distribution):
            url = reverse('distribution:current_rounders')
            response = self.client.get(url)
            distribution = Distribution.objects.first()
            ordered_rounder_line_items = distribution.return_ordered_rounder_line_items()
            data = {'form-TOTAL_FORMS': 9, 'form-INITIAL_FORMS': 9}
            starting_totals = [11, 12, 14, 15, 9, 8, 16, '', 14]
            starting_CCUs = [2, 5, 3, 7, 0, 1, 0, 1, 0]
            starting_COVIDs = [1, 2, 0, 0, 3, 0, 4, 3, 7]
            for i in range(9):
                data.update({f'form-{i}-id': i + 1})
                data.update({f'form-{i}-distribution_line_item': ordered_rounder_line_items[i].id})
                data.update({f'form-{i}-total_census': starting_totals[i]})
                data.update({f'form-{i}-CCU_census': starting_CCUs[i]})
                data.update({f'form-{i}-COVID_census': starting_COVIDs[i]})
            response = self.client.post(url, data=data)
            self.assertEqual(response.status_code, 200)

    def test_posting_invalid_data_to_view_displays_error_message(self):
        mock_distribution = \
            Distribution.objects.create_distribution_providers_roles_and_line_items_from_qgenda_relevant_data(
                date=timezone.localdate(), relevant_data=mock_qgenda_relevant_data)
        with mock.patch.object(DistributionManager, 'get_last_for_date_or_create_new', return_value=mock_distribution):
            url = reverse('distribution:current_rounders')
            response = self.client.get(url)
            distribution = Distribution.objects.first()
            ordered_rounder_line_items = distribution.return_ordered_rounder_line_items()
            data = {'form-TOTAL_FORMS': 9, 'form-INITIAL_FORMS': 9}
            starting_totals = [11, 12, 14, 15, 9, 8, 16, '', 14]
            starting_CCUs = [2, 5, 3, 7, 0, 1, 0, 1, 0]
            starting_COVIDs = [1, 2, 0, 0, 3, 0, 4, 3, 7]
            for i in range(9):
                data.update({f'form-{i}-id': i + 1})
                data.update({f'form-{i}-distribution_line_item': ordered_rounder_line_items[i].id})
                data.update({f'form-{i}-total_census': starting_totals[i]})
                data.update({f'form-{i}-CCU_census': starting_CCUs[i]})
                data.update({f'form-{i}-COVID_census': starting_COVIDs[i]})
            response = self.client.post(url, data=data)
        self.assertIn('This field is required', response.content.decode())


class ModifyRoundersViewTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        Provider.objects.create(qgenda_name='AnotherProvider')
        Provider.objects.create(qgenda_name='YetAnotherProvider')

    def test_view_resolves_url(self):
        url = f'/modify_rounders/07-20-20/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:modify_rounders')

    def test_view_gets_success_status_code(self):
        url = f'/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = f'/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}/'
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/modify_rounders.html')

    def test_view_context_contains_current_distribution(self):
        distribution = Distribution.objects.last()
        url = f'/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}/'
        response = self.client.get(url)
        self.assertIsInstance(response.context['distribution'], Distribution)
        self.assertEqual(response.context['distribution'], distribution)

    def test_view_context_contains_add_existing_provider_to_rounders_form(self):
        distribution = Distribution.objects.last()
        url = f'/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}/'
        response = self.client.get(url)
        self.assertIsInstance(response.context['add_rounder_from_existing_form'],
                              AddRounderFromExistingProvidersForm)

    def test_posting_to_view_adds_selected_provider_to_current_rounders_at_last_position_in_batting_order(self):
        distribution = Distribution.objects.last()
        url = reverse('distribution:modify_rounders', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(len(response.context['add_rounder_from_existing_form'].fields['provider'].queryset), 4)
        self.assertIn(Provider.objects.get(qgenda_name='YetAnotherProvider'),
                      response.context['add_rounder_from_existing_form'].fields['provider'].queryset)
        self.assertIn(Provider.objects.get(qgenda_name='AnotherProvider'),
                      response.context['add_rounder_from_existing_form'].fields['provider'].queryset)
        data = {'provider': Provider.objects.get(qgenda_name='YetAnotherProvider').id}
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        response = self.client.post(url, data=data)
        self.assertRedirects(response, url)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.display_name,
                         'YetAnotherProvider')
        response = self.client.get(url)
        self.assertEqual(len(response.context['add_rounder_from_existing_form'].fields['provider'].queryset), 3)
        self.assertNotIn(Provider.objects.get(qgenda_name='YetAnotherProvider'),
                         response.context['add_rounder_from_existing_form'].fields['provider'].queryset)
        self.assertIn(Provider.objects.get(qgenda_name='AnotherProvider'),
                      response.context['add_rounder_from_existing_form'].fields['provider'].queryset)
        data = {'provider': Provider.objects.get(qgenda_name='AnotherProvider').id}
        response = self.client.post(url, data=data)
        self.assertRedirects(response, url)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 6)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.display_name,
                         'AnotherProvider')
        response = self.client.get(url)
        self.assertEqual(len(response.context['add_rounder_from_existing_form'].fields['provider'].queryset), 2)
        self.assertNotIn(Provider.objects.get(qgenda_name='YetAnotherProvider'),
                         response.context['add_rounder_from_existing_form'].fields['provider'].queryset)
        self.assertNotIn(Provider.objects.get(qgenda_name='AnotherProvider'),
                         response.context['add_rounder_from_existing_form'].fields['provider'].queryset)


class AddRounderViewTests(TestCase):
    def test_view_resolves_url(self):
        url = f'/add_rounder/07-20-20/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:add_rounder')

    def test_view_gets_success_status_code(self):
        url = reverse('distribution:add_rounder', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = reverse('distribution:add_rounder', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/add_rounder.html')

    def test_view_context_contains_current_distribution(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        url = reverse('distribution:add_rounder', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertIsInstance(response.context['distribution'], Distribution)
        self.assertEqual(response.context['distribution'], distribution)

    def test_view_context_contains_add_new_rounder_form(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        url = reverse('distribution:add_rounder', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertIsInstance(response.context['add_new_rounder_form'], AddNewRounderForm)

    def test_posting_to_view_adds_a_new_provider_and_new_line_item(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        url = reverse('distribution:add_rounder', kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        data = {'input_name': 'provHaHa'}
        self.assertEqual(Provider.objects.count(), 6)
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.client.post(url, data=data)
        self.assertEqual(Provider.objects.count(), 7)
        self.assertEqual(Provider.objects.last().display_name, '_provHaHa')
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(distribution.return_ordered_rounder_line_items().last().provider.qgenda_name, '_provHaHa')


class MakeNextUpViewTests(TestCase):
    # non-displaying view that moves a given line item to next up
    def test_view_resolves_url(self):
        url = f'/make_next_up/{timezone.localdate().strftime("%m-%d-%y")}/15/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:make_next_up')

    def test_view_gets_redirect_status_code(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:make_next_up', kwargs={'line_item_id': 4,
                                                           'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_redirects_back_to_current_census_view(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provB', 'provC', 'provA', 'provD'])
        url = reverse('distribution:make_next_up', kwargs={'line_item_id': 4,
                                                           'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('distribution:current_rounders',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_going_to_view_makes_line_item_next_up(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provB', 'provC', 'provA', 'provD'])
        url = reverse('distribution:make_next_up', kwargs={'line_item_id': 4,
                                                           'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.client.get(url)
        self.assertEqual([line_item.provider.display_name for line_item in
                          distribution.return_ordered_rounder_line_items()], ['provD', 'provB', 'provC', 'provA'])


class ShiftUpInBattingOrderViewTests(TestCase):
    def test_view_resolves_url(self):
        url = f'/shift_up/{timezone.localdate().strftime("%m-%d-%y")}/15/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:shift_up_in_batting_order')

    def test_gets_redirect_status_code(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:shift_up_in_batting_order',
                      kwargs={'line_item_id': line_item_d.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_redirects_back_to_modify_rounders_view(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:shift_up_in_batting_order',
                      kwargs={'line_item_id': line_item_d.id,
                              'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('distribution:modify_rounders',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_going_to_view_shifts_rounder_up_one_spot(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:shift_up_in_batting_order',
                      kwargs={'line_item_id': line_item_d.id,
                              'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provC', 'provA', 'provD'])
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provC', 'provD', 'provA'])
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provD', 'provC', 'provA'])
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provD', 'provB', 'provC', 'provA'])
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provD', 'provB', 'provC', 'provA'])
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provD', 'provB', 'provC', 'provA'])
        line_item_c = distribution.return_ordered_rounder_line_items().get(provider__qgenda_name='provC')
        url = reverse('distribution:shift_up_in_batting_order',
                      kwargs={'line_item_id': line_item_c.id,
                              'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.client.get(url)
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provD', 'provC', 'provB', 'provA'])


class DeleteRounderViewTests(TestCase):
    def test_view_resolves_url(self):
        url = f'/delete_rounder/{timezone.localdate().strftime("%m-%d-%y")}/15/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:delete_rounder')

    def test_gets_redirect_status_code(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_d.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_redirects_back_to_modify_rounders_view(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_d.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('distribution:modify_rounders',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_going_to_view_shifts_rounder_up_one_spot(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        line_item_d = distribution.line_items.get(provider__qgenda_name='provD')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_d.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provC', 'provA', 'provD'])
        self.assertEqual(
            [line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 2, 3, 4])
        self.client.get(url)
        self.assertEqual(
            [line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 2, 3])
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provC', 'provA'])
        line_item_c = distribution.line_items.get(provider__qgenda_name='provC')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_c.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})

        self.client.get(url)
        self.assertEqual(
            [line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
            [1, 2])
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provB', 'provA'])
        line_item_b = distribution.line_items.get(provider__qgenda_name='provB')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_b.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.client.get(url)
        self.assertEqual(
            [line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
            [1])
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            ['provA'])
        line_item_a = distribution.line_items.get(provider__qgenda_name='provA')
        url = reverse('distribution:delete_rounder',
                      kwargs={'line_item_id': line_item_a.id, 'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.client.get(url)
        self.assertEqual(
            [line_item.position_in_batting_order for line_item in distribution.return_ordered_rounder_line_items()],
            [])
        self.assertEqual(
            [line_item.provider.qgenda_name for line_item in distribution.return_ordered_rounder_line_items()],
            [])


class ResetToQgendaViewTests(TestCase):
    def test_view_resolves_url(self):
        url = f'/reset_to_qgenda/{timezone.localdate().strftime("%m-%d-%y")}/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:reset_to_qgenda')

    def test_gets_redirect_status_code(self):
        url = reverse('distribution:reset_to_qgenda', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_redirects_back_to_main_view(self):
        url = reverse('distribution:reset_to_qgenda', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('distribution:current_rounders',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_going_to_view_creates_new_distribution_which_is_last_for_date(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:reset_to_qgenda', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.assertEqual(Distribution.objects.count(), 1)
        initial_distribution = Distribution.objects.last()
        self.client.get(url)
        self.assertEqual(Distribution.objects.count(), 2)
        new_distribution = Distribution.objects.last()
        self.assertNotEqual(initial_distribution, new_distribution)


class PatientCountViewTests(TestCase):
    def test_view_resolves_url(self):
        url = f'/patient_count/{timezone.localdate().strftime("%m-%d-%y")}/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:patient_count')

    def test_view_gets_success_status_code(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/patient_count.html')

    def test_view_context_contains_patient_count_form(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertIsInstance(response.context['patient_count_form'], PatientCountForm)

    def test_view_context_contains_date(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(response.context['date'], timezone.localdate())

    def test_view_context_contains_ordered_line_items(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.get(url)
        self.assertEqual(len(response.context['ordered_line_items']), 4)

    def test_posting_count_to_submit_count_redirects_to_designate_patients_view(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        response = self.client.post(url, data={'count_to_distribute': 5}, follow=True)
        self.assertRedirects(response, reverse('distribution:patient_characteristics',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_posting_count_to_edit_count_view_updates_the_count_to_distribute_and_instantiates_patients(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        url = reverse('distribution:patient_count', kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')})
        self.assertIsNone(Distribution.objects.first().count_to_distribute)
        self.client.post(url, data={'count_to_distribute': 13})
        self.assertEqual(Distribution.objects.first().count_to_distribute, 13)
        self.assertEqual(Patient.objects.count(), 13)
        for index, patient in enumerate(Patient.objects.all()):
            self.assertEqual(patient.distribution, Distribution.objects.first())
            self.assertEqual(patient.number_designation, index + 1)


class PatientCharacteristicsViewTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()
        for i in range(4):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)

    def test_view_resolves_url(self):
        url = f'/patient_characteristics/{timezone.localdate().strftime("%m-%d-%y")}/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:patient_characteristics')

    def test_view_gets_success_status_code(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/patient_characteristics.html')

    def test_view_context_contains_patient_characteristics_formset(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(len(response.context['patient_characteristics_formset']), 4)
        for form in response.context['patient_characteristics_formset']:
            self.assertIsInstance(form.instance, Patient)

    def test_formset_in_view_context_displays_rounders_only_as_options_for_bounce_to_dropdown(self):
        distribution = Distribution.objects.last()
        helper_fxn_add_4_non_rounder_line_items_to_distribution(distribution=distribution)
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        formset = response.context['patient_characteristics_formset']
        for form in formset.forms:
            self.assertEqual(form.fields['bounce_to'].choices.queryset.count(), 4)

    def test_view_context_contains_ordered_providers_with_starting_censuses(self):
        self.distribution = Distribution.objects.first()
        provider_names = ['provA', 'provB', 'provC', 'provD']
        totals = [10, 11, 13, 11]
        CCUs = [2, 3, 2, 1]
        COVIDs = [0, 3, 1, 2]
        orders = [3, 1, 2, 4]
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.context['ordered_line_items'].count(), 4)
        for index, line_item in enumerate(response.context['ordered_line_items']):
            if index == 0:
                self.assertEqual(line_item.id, 2)
                self.assertEqual(line_item.provider.display_name, 'provB')
                self.assertEqual(line_item.startingcensus.total_census, 11)
                self.assertEqual(line_item.startingcensus.CCU_census, 3)
                self.assertEqual(line_item.startingcensus.COVID_census, 3)
            elif index == 1:
                if index == 1:
                    self.assertEqual(line_item.id, 3)
                    self.assertEqual(line_item.provider.display_name, 'provC')
                    self.assertEqual(line_item.startingcensus.total_census, 13)
                    self.assertEqual(line_item.startingcensus.CCU_census, 2)
                    self.assertEqual(line_item.startingcensus.COVID_census, 1)
            elif index == 2:
                if index == 2:
                    self.assertEqual(line_item.id, 1)
                    self.assertEqual(line_item.provider.display_name, 'provA')
                    self.assertEqual(line_item.startingcensus.total_census, 10)
                    self.assertEqual(line_item.startingcensus.CCU_census, 2)
                    self.assertEqual(line_item.startingcensus.COVID_census, 0)
            elif index == 3:
                if index == 2:
                    self.assertEqual(line_item.id, 4)
                    self.assertEqual(line_item.provider.display_name, 'provD')
                    self.assertEqual(line_item.startingcensus.total_census, 11)
                    self.assertEqual(line_item.startingcensus.CCU_census, 1)
                    self.assertEqual(line_item.startingcensus.COVID_census, 0)

    def test_posting_data_to_view_updates_patient_characteristics(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
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
            'form-2-not_seen': True
        }
        self.client.post(url, data=data)
        self.assertEqual(Patient.objects.count(), 4)
        for i in range(4):
            patient = Patient.objects.get(number_designation=i+1)
            if i == 0:
                self.assertTrue(patient.COVID)
                self.assertFalse(patient.CCU)
            elif i == 3:
                self.assertTrue(patient.CCU)
                self.assertFalse(patient.COVID)
            else:
                self.assertFalse(patient.COVID)
                self.assertFalse(patient.CCU)
            if patient.number_designation in [2, 3]:
                self.assertEqual(patient.not_seen, True)
            else:
                self.assertEqual(patient.not_seen, False)

    def test_posting_data_to_view_redirects_to_patient_assignments_view(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
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
            'form-2-not_seen': True
        }
        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse('distribution:compose_patient_assignments_email',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_posting_data_to_view_assigns_patients_to_line_items(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        distribution = Distribution.objects.last()
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
            'form-2-not_seen': True
        }
        for line_item in distribution.return_ordered_rounder_line_items():
            self.assertEqual(line_item.assigned_patients.count(), 0)
        response = self.client.post(url, data=data)
        self.assertEqual(Patient.objects.count(), 4)
        for patient in Patient.objects.all():
            self.assertIsNotNone(patient.distribution_line_item)


    def test_troubleshooting_posting_data_to_view_WITH_BOUNCEBACKS_assigns_patients_to_line_items(self):
        url = reverse('distribution:patient_characteristics',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        distribution = Distribution.objects.last()
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
            'form-2-not_seen': True
        }
        for line_item in distribution.return_ordered_rounder_line_items():
            self.assertEqual(line_item.assigned_patients.count(), 0)
        response = self.client.post(url, data=data)
        self.assertEqual(Patient.objects.count(), 4)
        for patient in Patient.objects.all():
            self.assertIsNotNone(patient.distribution_line_item)
class ComposePatientAssignmentsEmailViewTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        distribution = Distribution.objects.last()

    def test_view_resolves_url(self):
        url = f'/compose_patient_assignments_email/{timezone.localdate().strftime("%m-%d-%y")}/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:compose_patient_assignments_email')

    def test_view_gets_success_status_code(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/compose_patient_assignments_email.html')

    def test_view_context_contains_date(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(response.context['date'], timezone.localdate())

    def test_view_context_contains_ordered_line_items(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(len(response.context['ordered_line_items']), 4)

    def test_view_context_contains_patient_assignment_dict(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(len(response.context['patient_assignment_dict']), 4)

    def test_view_context_contains_unassigned_patient_dict(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertEqual(len(response.context['unassigned_patient_dict']), 9)

    def test_assigned_patients_appear_in_expected_places_within_patient_assignment_dict(self):
        distribution = Distribution.objects.last()
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                self.assertEqual(patients_in_subset.count(), 0)
        patient1 = Patient.objects.create(number_designation=1, distribution=distribution, COVID=False, CCU=False,
                                          not_seen=False, bounce_to=None,
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)
        patient2 = Patient.objects.create(number_designation=2, distribution=distribution, COVID=True, CCU=False,
                                          not_seen=False, bounce_to=None,
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_covid_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient2, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)
        patient3 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=True,
                                          not_seen=False, bounce_to=None,
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_covid_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient2, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)
        patient4 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=False,
                                          not_seen=True, bounce_to=None,
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_covid_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient2, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'not_seen_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient4, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)
        patient5 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=False,
                                          not_seen=False, bounce_to=Provider.objects.get(qgenda_name='provB'),
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_covid_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient2, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'not_seen_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient4, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_bounceback_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient5, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)
        patient6 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=True, CCU=True,
                                          not_seen=False, bounce_to=None,
                                          distribution_line_item=DistributionLineItem.objects.get(
                                              provider__display_name='provB'))
        response = self.client.get(url)
        for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
            for subset, patients_in_subset in patient_subsets.items():
                if line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_neg_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient1, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_covid_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient2, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient3, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'not_seen_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient4, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_bounceback_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient5, patients_in_subset)
                elif line_item == DistributionLineItem.objects.get(
                        provider__display_name='provB') and subset == 'seen_dual_pos_pts':
                    self.assertEqual(patients_in_subset.count(), 1)
                    self.assertIn(patient6, patients_in_subset)
                else:
                    self.assertEqual(patients_in_subset.count(), 0)

    def test_view_context_contains_email_distribution_form(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        response = self.client.get(url)
        self.assertIsInstance(response.context['email_distribution_form'], EmailDistributionForm)

    def test_posting_form_creates_a_distribution_email_and_sends_it(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        email_addressee_start_values = [('Hospitalists', 'test1@test.com', True, True),
                                        ('Cheryl', 'test2@test.com', True, True),
                                        ('Susan', 'test3@test.com', True, True),
                                        ('Intensivists', 'test4@test.com', True, False),
                                        ('ID docs', 'test5@test.com', True, False)]
        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        data = {'subject': 'test_subject', 'recipient_choices': [1, 4, 5]}
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(url, data=data)
        self.assertEqual(DistributionEmail.objects.count(), 1)
        email = DistributionEmail.objects.last()
        for snippet in ['test1@', 'test4@', 'test5@']:
            self.assertIn(snippet, email.recipient_text_field)
        for snippet in ['test2@', 'test3@']:
            self.assertNotIn(snippet, email.recipient_text_field)
        self.assertEqual(len(mail.outbox), 1)

    def test_posting_form_redirects_to_patient_distribution_view(self):
        url = reverse('distribution:compose_patient_assignments_email',
                      kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        email_addressee_start_values = [('Hospitalists', 'test1@test.com', True, True),
                                        ('Cheryl', 'test2@test.com', True, True),
                                        ('Susan', 'test3@test.com', True, True),
                                        ('Intensivists', 'test4@test.com', True, False),
                                        ('ID docs', 'test5@test.com', True, False)]
        for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
            EmailAddressee.objects.create(displayed_name=displayed_name, email_address=email_address,
                                          visible=visible, pre_checked=pre_checked)
        data = {'subject': 'test_subject', 'recipient_choices': [1, 4, 5]}
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse('distribution:view_patient_assignments',
                                               kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")}))

        # def test_unassigned_patients_appear_in_expected_places_within_unassigned_patient_dict(self):
        #     distribution = Distribution.objects.last()
        #     url = reverse('distribution:patient_assignments',
        #                   kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['unassigned_patient_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             self.assertEqual(patients_in_subset.count(), 0)
        #     patient1 = Patient.objects.create(number_designation=1, distribution=distribution, COVID=False, CCU=False,
        #                                       not_seen=False,bounce_to=None,
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #     patient2 = Patient.objects.create(number_designation=2, distribution=distribution, COVID=True, CCU=False,
        #                                       not_seen=False,bounce_to=None,
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_covid_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient2, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #     patient3 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=True,
        #                                       not_seen=False,bounce_to=None,
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_covid_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient2, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #     patient4 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=False,
        #                                       not_seen=True,bounce_to=None,
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_covid_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient2, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'not_seen_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient4, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #     patient5 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=False, CCU=False,
        #                                       not_seen=False,bounce_to=Provider.objects.get(qgenda_name='provB'),
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_covid_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient2, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'not_seen_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient4, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_bounceback_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient5, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #     patient6 = Patient.objects.create(number_designation=3, distribution=distribution, COVID=True, CCU=True,
        #                                       not_seen=False,bounce_to=None,
        #                                       distribution_line_item=DistributionLineItem.objects.get(
        #                                           provider__display_name='provB'))
        #     response = self.client.get(url)
        #     for line_item, patient_subsets in response.context['patient_assignment_dict'].items():
        #         for subset, patients_in_subset in patient_subsets.items():
        #             if line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_dual_neg_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient1, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                     provider__display_name='provB') and subset=='seen_covid_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient2, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_ccu_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient3, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'not_seen_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient4, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_bounceback_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient5, patients_in_subset)
        #             elif line_item == DistributionLineItem.objects.get(
        #                 provider__display_name='provB') and subset == 'seen_dual_pos_pts':
        #                 self.assertEqual(patients_in_subset.count(), 1)
        #                 self.assertIn(patient6, patients_in_subset)
        #             else:
        #                 self.assertEqual(patients_in_subset.count(), 0)
        #
        #     self.fail('finish')

    class SendDistributionTests(TestCase):
        def setUp(self):
            helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
            distribution = Distribution.objects.last()
            for i in range(4):
                Patient.objects.create(distribution=distribution, number_designation=i + 1)

        def test_view_resolves_url(self):
            url = f'/send_distribution/{timezone.localdate().strftime("%m-%d-%y")}/'
            view = resolve(url)
            self.assertEqual(view.view_name, 'distribution:send_distribution')

        def test_view_gets_redirect_status_code(self):
            url = reverse('distribution:send_distribution',
                          kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

        def test_view_redirects_to_distribution(self):
            url = reverse('distribution:send_distribution',
                          kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")})
            response = self.client.get(url)
            self.assertRedirects(response, reverse('distribution:patient_assignments',
                                                   kwargs={'date_str': timezone.localdate().strftime("%m-%d-%y")}))

class UpdateProviderViewTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()

    def test_view_resolves_url(self):
        url = f'/update_provider/provA/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:update_provider')

    def test_view_gets_success_status_code(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'distribution/update_provider.html')

    def test_view_context_contains_provider_form_belonging_to_correct_provider_instance(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        response = self.client.get(url)
        self.assertIsInstance(response.context['provider_update_form'], ProviderUpdateForm)

    def test_posting_to_view_updates_provider_values(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        data = {'display_name': 'Iggy', 'max_total_census': 14, 'max_CCU_census': 5, 'max_COVID_census': 3}
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.display_name, 'provA')
        self.assertEqual(provider.max_total_census, 17)
        self.assertEqual(provider.max_CCU_census, 17)
        self.assertEqual(provider.max_COVID_census, 17)
        self.client.post(url, data=data)
        provider = Provider.objects.first()
        self.assertEqual(provider.display_name, 'Iggy')
        self.assertEqual(provider.max_total_census, 14)
        self.assertEqual(provider.max_CCU_census, 5)
        self.assertEqual(provider.max_COVID_census, 3)

    def test_posting_valid_data_to_view_redirects_to_current_rounder_page(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        data = {'display_name': 'Iggy', 'max_total_census': 14, 'max_CCU_census': 5, 'max_COVID_census': 3}
        response = self.client.post(url, data=data)
        provider = Provider.objects.first()
        self.assertEqual(provider.display_name, 'Iggy')
        self.assertEqual(provider.max_total_census, 14)
        self.assertEqual(provider.max_CCU_census, 5)
        self.assertEqual(provider.max_COVID_census, 3)
        self.assertRedirects(response, reverse('distribution:current_rounders',
                                               kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))

    def test_posting_invalid_data_stays_on_the_page(self):
        url = reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'})
        data = {'display_name': 'Dysdiadochokinesia', 'max_total_census': 14, 'max_CCU_census': 5,
                'max_COVID_census': 3}
        response = self.client.post(url, data=data)
        provider = Provider.objects.first()
        self.assertEqual(response.status_code, 200)

class UpdateMaxCensusViewTests(TestCase):
    def setUp(self):
        helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()

    def test_view_resolves_url(self):
        url = f'/set_max_censuses/default/provA/'
        view = resolve(url)
        self.assertEqual(view.view_name, 'distribution:set_max_censuses')

    def test_view_gets_redirect_status_code(self):
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'default', 'provider_qgenda_name': 'provA'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_view_resets_provider_maxima_to_default_teaching_orienting_or_COVID_free(self):
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'orienting', 'provider_qgenda_name': 'provA'})
        provider = Provider.objects.get(qgenda_name='provA')
        provider.max_COVID_census, provider.max_CCU_census, provider.max_total_census = 2, 5, 12
        provider.save()
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 5)
        self.assertEqual(provider.max_COVID_census, 2)
        self.client.get(url)
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 12)
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'default', 'provider_qgenda_name': 'provA'})
        self.client.get(url)
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.max_total_census, 17)
        self.assertEqual(provider.max_CCU_census, 17)
        self.assertEqual(provider.max_COVID_census, 17)
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'teaching', 'provider_qgenda_name': 'provA'})
        self.client.get(url)
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 12)
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'COVID-free', 'provider_qgenda_name': 'provA'})
        self.client.get(url)
        provider = Provider.objects.get(qgenda_name='provA')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 0)

    def test_view_redirects_to_update_provider_view(self):
        url = reverse('distribution:set_max_censuses',
                      kwargs={'census_track': 'default', 'provider_qgenda_name': 'provA'})
        response = self.client.get(url)
        self.assertRedirects(response,
                             reverse('distribution:update_provider', kwargs={'provider_qgenda_name': 'provA'}))
