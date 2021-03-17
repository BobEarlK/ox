import random, time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.utils import timezone

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.ui import Select, WebDriverWait

from contextlib import contextmanager

from .. import helper_fxns
from ..models import Distribution, Provider, Patient

MAX_WAIT = 99


class FunctionalTest(StaticLiveServerTestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    @contextmanager
    def wait_for_page_load(self, timeout=30):
        old_page = self.browser.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.browser, timeout).until(
            staleness_of(old_page)
        )

    def wait_for(self, fn):
        start_time = time.time()
        while True:
            time.sleep(1)
            try:
                return fn()
            except (WebDriverException, AssertionError) as e:
                if time.time() - start_time > MAX_WAIT:
                    raise e


class WalkThroughTest(FunctionalTest):
    def test_walkthrough_part_one(self):
        # Z navigates to home page for the first time, and notes the correct title of the page.
        self.browser.get(f'{self.live_server_url}')
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she also sees a list of providers
        rounder_names = self.browser.find_elements_by_id('id_rounder_name')
        a_few_rounder_names = ['Siew', 'Amrit', 'Au', 'Pelley', 'Connor', 'Graesser', 'Stuart', 'KochLeibmann',
                               'Booms', 'Gordon', 'Addison', 'Davis', 'Bowen', 'KellyHedrick']
        self.assertTrue(any(
            name in a_few_rounder_names for name in [rounder_name.text for rounder_name in rounder_names]))
        # Z needs to change rounders due to an illness
        # we will add a provider to the database so that she can select it later
        Provider.objects.create(qgenda_name='TestA')
        modify_rounders_button = self.browser.find_element_by_id('id_modify_rounders_link')
        modify_rounders_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she looks to see if the provider in the database is listed in the dropdown list of existing providers
        add_rounder_from_existing_select = Select(
            self.browser.find_element_by_id('id_add_rounder_from_existing_form').find_element_by_tag_name('select'))
        initial_alternate_provider_choices = add_rounder_from_existing_select.options
        self.assertGreaterEqual(len(initial_alternate_provider_choices), 2)
        self.assertIn('TestA', [rounder_choice.text for rounder_choice in add_rounder_from_existing_select.options])
        # she removes the rounders in the second and then in the 4th position
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        starting_rounder_count = len(rounder_rows)
        rounder_rows[1].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        rounder_rows[3].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual(len(rounder_rows), starting_rounder_count - 2)
        # she notices that the dropdown for adding from existing is now longer by 2 (with the 2 providers removed)
        add_rounder_from_existing_select = Select(
            self.browser.find_element_by_id('id_add_rounder_from_existing_form').find_element_by_tag_name('select'))
        self.assertEqual(len(add_rounder_from_existing_select.options), len(initial_alternate_provider_choices) + 2)
        # she adds TestA to the list of rounders.
        add_rounder_from_existing_select.select_by_visible_text('TestA')
        self.browser.find_element_by_id('id_add_rounder_from_existing_button').click()
        # she wants to add a provider not on the list, TestB.  NOTE:  kept getting an error that object not clickable, though
        # was able to click outside of testing, so navigating there manually, fingers crossed
        # she is taken to the add_new_rounder page
        self.browser.get(f'{self.live_server_url}/add_rounder/{timezone.localdate().strftime("%m-%d-%y")}')
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Add Rounder - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.find_element_by_id('id_input_name').send_keys('TestB')
        self.browser.find_element_by_id('id_add_new_rounder_button').click()
        # she is taken back to the modify rounders page, and sees that TestA and _TestB have been added to bring up the
        # number of rows to the original number
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual(len(rounder_rows), starting_rounder_count)
        self.assertEqual(rounder_rows[-2].find_element_by_id('id_provider_cell').text, 'TestA')
        self.assertEqual(rounder_rows[-1].find_element_by_id('id_provider_cell').text, '_TestB')
        # she reorders the providers, moving TestA up twice, then moving TestB to the top
        rounder_rows[-2].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        rounder_rows[-3].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        rounder_rows[-1].find_element_by_class_name('next-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual(rounder_rows[-3].find_element_by_id('id_provider_cell').text, 'TestA')
        self.assertEqual(rounder_rows[0].find_element_by_id('id_provider_cell').text, '_TestB')
        # she clicks the button to return to the main page
        self.browser.find_element_by_id('id_return_to_main_page_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she enters in values for the censuses and submits the form
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        for index, row in enumerate(rounder_rows):
            row.find_element_by_id('id_total_census_field').send_keys(f'{9 + index % 4}')
            row.find_element_by_id('id_CCU_census_field').send_keys(f'{0 + index % 3}')
            row.find_element_by_id('id_COVID_census_field').send_keys(f'{0 + index % 2}')
        self.browser.find_element_by_id('id_submit_censuses_button').click()
        # she is taken to the patient count page, where she enters the count and submits
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.find_element_by_id('id_count_to_distribute').send_keys('22')
        self.browser.find_element_by_id('id_submit_count_button').click()
        # she is taken to the patient characteristics page, where she designates the patients
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for index, patient_card in enumerate(patient_cards):
            if not index % 3:
                patient_card.find_element_by_class_name('CCU-checkbox').click()
            if not index % 7:
                patient_card.find_element_by_class_name('COVID-checkbox').click()
            if not index % 5:
                patient_card.find_element_by_class_name('not-seen-checkbox').click()
            if not index % 4:
                bounceback_select = Select(
                    patient_card.find_element_by_class_name('bounce-row').find_element_by_tag_name('select'))
                bounceback_select.select_by_index(index % 5)
        self.browser.find_element_by_id('id_submit_patient_forms').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # After all of that Z realizes she made an error, and backs up to the beginning
        self.browser.back()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.back()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.back()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        # she notes she is back at the current rounders page
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she clicks to reset to the QGenda rounders
        self.browser.find_element_by_id('id_modify_rounders_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.find_element_by_id('id_revert_to_QGenda_data').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        # she notes she is back at the current rounders page, and TestA and TestB are gone
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        for name in ['TestA', '_TestB']:
            self.assertNotIn(name, [row.find_element_by_id('id_rounder_name').text for row in rounder_rows])

    def test_walkthrough_part_two(self):
        self.browser.get(f'{self.live_server_url}')
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # One of the rounders is a teaching attending, so she makes that change
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        teaching_rounder_field = rounder_rows[4].find_element_by_id('id_rounder_name')
        teaching_rounder_name = teaching_rounder_field.text
        teaching_rounder_field.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update {teaching_rounder_name}')
        self.browser.find_element_by_id('id_set_max_censuses_to_teaching').click()
        self.browser.find_element_by_id('id_submit_provider_updates').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she changes the displayed name for another rounder, sets arbitrary limits, and moves that provider to next up
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        custom_rounder_field = rounder_rows[6].find_element_by_id('id_rounder_name')
        custom_rounder_name = custom_rounder_field.text
        custom_rounder_field.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update {custom_rounder_name}')
        self.browser.find_element_by_id('id_display_name').click()
        self.browser.find_element_by_id('id_display_name').send_keys('Iggy')
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('13')
        self.browser.find_element_by_id('id_max_CCU_census').click()
        self.browser.find_element_by_id('id_max_CCU_census').send_keys('1')
        self.browser.find_element_by_id('id_max_COVID_census').click()
        self.browser.find_element_by_id('id_max_COVID_census').send_keys('1')
        self.browser.find_element_by_id('id_submit_provider_updates').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        rounder_rows[6].find_element_by_id('id_next_up_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        self.assertEqual(rounder_rows[0].find_element_by_id('id_rounder_name').text, 'Iggy')
        self.assertEqual(
            rounder_rows[0].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-total-census').text, '13')
        self.assertEqual(
            rounder_rows[0].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-CCU-census').text, '1')
        self.assertEqual(
            rounder_rows[0].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-COVID-census').text, '1')
        self.assertEqual(
            rounder_rows[7].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-total-census').text, '12')
        self.assertEqual(
            rounder_rows[7].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-CCU-census').text, '12')
        self.assertEqual(
            rounder_rows[7].find_element_by_id('id_rounder_cell').find_element_by_class_name(
                'custom-max-COVID-census').text, '12')
        # she fills in the subsequent forms and sees that the totals are respected
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        for index, row in enumerate(rounder_rows):
            row.find_element_by_id('id_total_census_field').send_keys(f'{11 + index % 4}')
            row.find_element_by_id('id_CCU_census_field').send_keys(f'{0 + index % 3}')
            row.find_element_by_id('id_COVID_census_field').send_keys(f'{0 + index % 2}')
        self.browser.find_element_by_id('id_submit_censuses_button').click()
        # she is taken to the patient count page, where she enters the count and submits
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.find_element_by_id('id_count_to_distribute').send_keys('27')
        self.browser.find_element_by_id('id_submit_count_button').click()
        # she is taken to the patient characteristics page, where she designates the patients
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for index, patient_card in enumerate(patient_cards):
            if not index % 3:
                patient_card.find_element_by_class_name('CCU-checkbox').click()
            if not index % 7:
                patient_card.find_element_by_class_name('COVID-checkbox').click()
            if not index % 5:
                patient_card.find_element_by_class_name('not-seen-checkbox').click()
            if not index % 4:
                bounceback_select = Select(
                    patient_card.find_element_by_class_name('bounce-row').find_element_by_tag_name('select'))
                bounceback_select.select_by_index(index % 5)
        self.browser.find_element_by_id('id_submit_patient_forms').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')

    def troubleshoot_patients_assigned_out_of_order_and_error_assigning_to_added_rounder(self):
        self.browser.get(f'{self.live_server_url}')
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # she also sees a list of providers
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        rounder_rows[-1].find_element_by_id('id_next_up_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_modify_rounders_link').click()
        add_rounder_cell = self.browser.find_element_by_id('id_add_rounder_from_existing_form')
        add_rounder_selection = Select(add_rounder_cell.find_element_by_tag_name('select'))
        add_rounder_selection.select_by_index(5)
        self.browser.find_element_by_id('id_add_rounder_from_existing_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_return_to_main_page_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        rounder_rows[8].find_element_by_id('id_rounder_name').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_max_CCU_census').click()
        self.browser.find_element_by_id('id_max_CCU_census').send_keys('10')
        self.browser.find_element_by_id('id_max_COVID_census').click()
        self.browser.find_element_by_id('id_max_COVID_census').send_keys('10')
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('10')
        self.browser.find_element_by_id('id_submit_provider_updates').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        rounder_rows[9].find_element_by_id('id_rounder_name').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('7')
        self.browser.find_element_by_id('id_submit_provider_updates').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        rounder_rows = self.browser.find_elements_by_id('id_starting_census_row')
        for index, (total_patients, CCU_patients, COVID_patients) in enumerate([
            (13, 0, 0), (13, 0, 0), (13, 2, 0), (14, 1, 0), (15, 1, 2), (15, 1, 2), (15, 1, 0), (16, 1, 0), (
                    11, 0, 0), (7, 1, 1)]):
            rounder_rows[index].find_element_by_id('id_total_census_field').send_keys(str(total_patients))
            rounder_rows[index].find_element_by_id('id_CCU_census_field').send_keys(str(CCU_patients))
            rounder_rows[index].find_element_by_id('id_COVID_census_field').send_keys(str(COVID_patients))
        self.browser.find_element_by_id('id_submit_censuses_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_count_to_distribute').send_keys('19')
        self.browser.find_element_by_id('id_submit_count_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for index, patient_card in enumerate(patient_cards):
            if index in [2,8,11,13,18]:
                patient_card.find_element_by_class_name('CCU-checkbox').click()
        self.browser.find_element_by_id('id_submit_patient_forms').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        pass


class CurrentRoundersTest(FunctionalTest):
    # Z navigates to home page for the first time, and notes the correct title of the page.  She notes
    # that anytime a page is loaded, a new distribution is created
    def test_going_to_main_site_loads_current_rounders_view_and_creates_new_distribution(self):
        self.browser.get(f'{self.live_server_url}')
        self.browser.get(f'{self.live_server_url}/current_rounders/{timezone.localdate().strftime("%-m-%-d-%y")}/')
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.assertEqual(Distribution.objects.count(), 1)

        # Since no distribution has been created for the current date, the distribution_line_items created are those
        # from qgenda
        rounder_names = self.browser.find_elements_by_id('id_rounder_name')
        a_few_rounder_names = ['Siew', 'Amrit', 'Au', 'Pelley', 'Connor', 'Graesser', 'Stuart', 'KochLeibmann',
                               'Booms', 'Gordon', 'Addison', 'Davis', 'Bowen', 'KellyHedrick']
        self.assertTrue(any(
            name in a_few_rounder_names for name in [rounder_name.text for rounder_name in rounder_names]))
        # Z fills out the form and submits, and is taken to the enter patient count page
        rows = self.browser.find_elements_by_id('id_starting_census_row')
        for row in rows:
            total_census_box = row.find_element_by_id('id_total_census_field')
            total_census_box.send_keys('13')
            CCU_census_box = row.find_element_by_id('id_CCU_census_field')
            CCU_census_box.send_keys('2')
            COVID_census_box = row.find_element_by_id('id_COVID_census_field')
            COVID_census_box.send_keys('4')
        submit_button = self.browser.find_element_by_id('id_submit_censuses_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        #  there is still only one distribution, the correct number of line_items, and the correct starting census
        distribution = Distribution.objects.first()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), len(rows))
        for line_item in distribution.return_ordered_rounder_line_items():
            self.assertEqual(line_item.startingcensus.total_census, 13)
            self.assertEqual(line_item.startingcensus.CCU_census, 2)
            self.assertEqual(line_item.startingcensus.COVID_census, 4)

        # Z wants to go back, and notes that the form is still filled out with the same values
        self.browser.back()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rows = self.browser.find_elements_by_id('id_starting_census_row')
        for row in rows:
            total_census_box = row.find_element_by_id('id_total_census_field')
            self.assertEqual(total_census_box.get_attribute('value'), '13')
            CCU_census_box = row.find_element_by_id('id_CCU_census_field')
            self.assertEqual(CCU_census_box.get_attribute('value'), '2')
            COVID_census_box = row.find_element_by_id('id_COVID_census_field')
            self.assertEqual(COVID_census_box.get_attribute('value'), '4')

        # Z wants to see what happens when she submits an incomplete form, fills out all but the last line of the form
        rows = self.browser.find_elements_by_id('id_starting_census_row')
        a_total_census_box = rows[4].find_element_by_id('id_total_census_field')
        a_total_census_box.click()
        a_total_census_box.send_keys(Keys.BACKSPACE)
        submit_button = self.browser.find_element_by_id('id_submit_censuses_button')
        self.assertEqual(0, len(self.browser.find_elements_by_css_selector('.is-invalid')))
        submit_button.click()
        # Z sees an error message, and stays on the same page
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(1, len(self.browser.find_elements_by_css_selector('.is-invalid')))


class ModifyRoundersTest(FunctionalTest):
    def test_displays_current_rounders(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provC', 'provA', 'provD'])

    def test_make_next_up_function_promotes_line_item_to_next_up_and_returns_to_page(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provC', 'provA', 'provD'])
        rounder_rows[2].find_element_by_class_name('next-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provA', 'provD', 'provB', 'provC'])
        rounder_rows[3].find_element_by_class_name('next-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provC', 'provA', 'provD', 'provB'])
        rounder_rows[1].find_element_by_class_name('next-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provA', 'provD', 'provB', 'provC'])
        rounder_rows[0].find_element_by_class_name('next-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provA', 'provD', 'provB', 'provC'])

    def test_shift_up_function_shifts_line_item_up_and_returns_to_page(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provC', 'provA', 'provD'])
        rounder_rows[2].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provA', 'provC', 'provD'])
        rounder_rows[3].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provA', 'provD', 'provC'])
        rounder_rows[1].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provA', 'provB', 'provD', 'provC'])
        rounder_rows[0].find_element_by_class_name('shift-up-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provA', 'provB', 'provD', 'provC'])

    def test_delete_function_deletes_line_item_up_and_returns_to_page(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provC', 'provA', 'provD'])
        rounder_rows[2].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provC', 'provD'])
        rounder_rows[1].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provB', 'provD'])
        rounder_rows[0].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual([row.find_element_by_id('id_provider_cell').text for row in rounder_rows],
                         ['provD'])
        rounder_rows[0].find_element_by_class_name('delete-link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        rounder_rows = self.browser.find_elements_by_id('id_rounder_row')
        self.assertEqual(len(rounder_rows), 0)

    def test_can_add_rounder_from_list_of_existing_rounders(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        Provider.objects.create(qgenda_name='AnotherProvider')
        Provider.objects.create(qgenda_name='YetAnotherProvider')
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        add_rounder_cell = self.browser.find_element_by_id('id_add_rounder_from_existing_form')
        add_rounder_selection = Select(add_rounder_cell.find_element_by_tag_name('select'))
        add_rounder_selection.select_by_index(2)
        distribution = Distribution.objects.last()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.browser.find_element_by_id('id_add_rounder_from_existing_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        add_rounder_cell = self.browser.find_element_by_id('id_add_rounder_from_existing_form')
        add_rounder_selection = Select(add_rounder_cell.find_element_by_tag_name('select'))
        add_rounder_selection.select_by_index(1)
        self.browser.find_element_by_id('id_add_rounder_from_existing_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 6)

    def test_added_rounder_appears_on_patient_characteristics_page_among_options_for_bouncebacks(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        Provider.objects.create(qgenda_name='AnotherProvider')
        Provider.objects.create(qgenda_name='YetAnotherProvider')
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        add_rounder_cell = self.browser.find_element_by_id('id_add_rounder_from_existing_form')
        add_rounder_selection = Select(add_rounder_cell.find_element_by_tag_name('select'))
        add_rounder_selection.select_by_index(2)
        distribution = Distribution.objects.last()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.browser.find_element_by_id('id_add_rounder_from_existing_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.find_element_by_id('id_return_to_main_page_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))


class NewRounderTests(FunctionalTest):
    def test_inputting_new_rounder_creates_new_provider_and_new_line_item_and_redirects_to_modify_rounders(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/modify_rounders/{timezone.localdate().strftime("%m-%d-%y")}')
        self.fail('Selenium fails here, but can click through and add rounder in practice')
        self.browser.find_element_by_id('id_add_new_rounder_link').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Add Rounder - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.find_element_by_id('id_input_name').send_keys('Newby')
        distribution = Distribution.objects.last()
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 4)
        self.assertEqual(Provider.objects.count(), 6)
        self.browser.find_element_by_id('id_add_new_rounder_button').click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Modify Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.assertEqual(distribution.return_ordered_rounder_line_items().count(), 5)
        self.assertEqual(Provider.objects.count(), 7)
        provider = Provider.objects.last()
        self.assertEqual(provider.qgenda_name, '_Newby')


class PatientCountTests(FunctionalTest):
    # def test_displays_dummy_distribution(self):
    #     helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
    #     self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
    #     self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
    #     starting_census_table = self.browser.find_element_by_id('id_starting_census_form')
    #     rounder_rows = starting_census_table.find_elements_by_id('id_rounder_row')
    #     expected_providers = ['provB', 'provC', 'provA', 'provD']
    #     expected_totals = [11, 13, 10, 11]
    #     expected_CCUs = [3, 2, 2, 1]
    #     expected_COVIDs = [3, 1, 0, 2]
    #     for index, rounder_row in enumerate(rounder_rows):
    #         provider_cell = rounder_row.find_element_by_id('id_provider_cell')
    #         self.assertEqual(provider_cell.text, expected_providers[index])
    #         total_census_cell = rounder_row.find_element_by_id('id_total_census_cell')
    #         self.assertEqual(int(total_census_cell.text), expected_totals[index])

    def test_entering_count_and_submitting_creates_patients_and_goes_to_patient_characteristics_page(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('31')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        # submit_button = self.browser.find_element_by_id('id_submit_rounder_button')
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.assertEqual(Distribution.objects.count(), 1)
        self.assertEqual(Distribution.objects.first().patients.count(), 31)


class PatientCharacteristicsTests(FunctionalTest):
    def test_submitting_patient_characteristics_sets_characteristics_and_goes_to_patient_assignments_page(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('31')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        self.browser.maximize_window()
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for i in [0, 13, 14, 17]:
            patient_cards[i].find_element_by_class_name('CCU-checkbox').click()
            patient_cards[i + 3].find_element_by_class_name('COVID-checkbox').click()
            patient_cards[i + 6].find_element_by_class_name('not-seen-checkbox').click()
        submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
        submit_patient_forms_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
        for i in range(31):
            patient = Distribution.objects.first().patients.get(number_designation=i + 1)
            if i in [0, 13, 14, 17]:
                self.assertTrue(patient.CCU)
            else:
                self.assertFalse(patient.CCU)
            if i - 3 in [0, 13, 14, 17]:
                self.assertTrue(patient.COVID)
            else:
                self.assertFalse(patient.COVID)
            if i - 6 in [0, 13, 14, 17]:
                self.assertTrue(patient.not_seen)
            else:
                self.assertFalse(patient.not_seen)


class ComposePatientAssignmentEmailTests(FunctionalTest):
    def test_patients_are_distributed_as_expected_CASE_no_not_seen_many_over_cap(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('31')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for i in [0, 13, 14, 17]:
            patient_cards[i].find_element_by_class_name('CCU-checkbox').click()
            patient_cards[i + 3].find_element_by_class_name('COVID-checkbox').click()
        submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
        submit_patient_forms_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
        unassigned_row = self.browser.find_element_by_id('id_unassigned_patient_row')
        unassigned_dual_neg_pts = unassigned_row.find_element_by_class_name('dual-neg-text')
        for i in range(24, 32):
            self.assertIn(str(i), unassigned_dual_neg_pts.text)
        unassigned_ending_numbers = unassigned_row.find_element_by_class_name('ending-numbers')
        self.assertEqual(int(unassigned_ending_numbers.find_element_by_class_name('total-text').text), 8)
        self.assertEqual(int(unassigned_ending_numbers.find_element_by_class_name('CCU-text').text), 0)
        self.assertEqual(int(unassigned_ending_numbers.find_element_by_class_name('COVID-text').text), 0)
        provider_rows = self.browser.find_elements_by_id('id_assigned_patient_row')
        self.assertEqual(provider_rows[0].find_element_by_id('id_provider_name').text, 'provB')
        for i in [2, 3, 5, 6, 7, 8]:
            self.assertIn(str(i), provider_rows[0].find_element_by_id('id_dual_neg_patients').text)
        self.assertEqual(
            int(provider_rows[0].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'total-text').text),
            17)
        self.assertEqual(
            int(provider_rows[0].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'CCU-text').text),
            3)
        self.assertEqual(
            int(provider_rows[0].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'COVID-text').text),
            3)
        self.assertEqual(provider_rows[1].find_element_by_id('id_provider_name').text, 'provC')
        for i in [1]:
            self.assertIn(str(i), provider_rows[1].find_element_by_id('id_CCU_patients').text)
        for i in [4]:
            self.assertIn(str(i), provider_rows[1].find_element_by_id('id_COVID_patients').text)
        for i in [9, 10]:
            self.assertIn(str(i), provider_rows[1].find_element_by_id('id_dual_neg_patients').text)
        self.assertEqual(
            int(provider_rows[1].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'total-text').text),
            17)
        self.assertEqual(
            int(provider_rows[1].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'CCU-text').text),
            3)
        self.assertEqual(
            int(provider_rows[1].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'COVID-text').text),
            2)
        self.assertEqual(provider_rows[2].find_element_by_id('id_provider_name').text, 'provA')
        for i in [18]:
            self.assertIn(str(i), provider_rows[2].find_element_by_id('id_dual_pos_patients').text)
        for i in [17]:
            self.assertIn(str(i), provider_rows[2].find_element_by_id('id_COVID_patients').text)
        for i in [11, 12, 13, 16, 19]:
            self.assertIn(str(i), provider_rows[2].find_element_by_id('id_dual_neg_patients').text)
        self.assertEqual(
            int(provider_rows[2].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'total-text').text),
            17)
        self.assertEqual(
            int(provider_rows[2].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'CCU-text').text),
            3)
        self.assertEqual(
            int(provider_rows[2].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'COVID-text').text),
            2)
        self.assertEqual(provider_rows[3].find_element_by_id('id_provider_name').text, 'provD')
        for i in [14, 15]:
            self.assertIn(str(i), provider_rows[3].find_element_by_id('id_CCU_patients').text)
        for i in [21]:
            self.assertIn(str(i), provider_rows[3].find_element_by_id('id_COVID_patients').text)
        for i in [20, 22, 23]:
            self.assertIn(str(i), provider_rows[3].find_element_by_id('id_dual_neg_patients').text)
        self.assertEqual(
            int(provider_rows[3].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'total-text').text),
            17)
        self.assertEqual(
            int(provider_rows[3].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'CCU-text').text),
            3)
        self.assertEqual(
            int(provider_rows[3].find_element_by_class_name('ending-numbers').find_element_by_class_name(
                'COVID-text').text),
            3)

    def test_patients_are_distributed_as_expected_CASE_many_unseen(self):
        # not_seens, which are distributed
        # in order of dual-pos, CCU-pos, COVID-pos, and dual-neg
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('16')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for i in [0, 2, 5, 7, 10, 11, 14]:
            patient_cards[i].find_element_by_class_name('not-seen-checkbox').click()
        for i in [1, 2, 5, 6, 8, 11, 12]:
            patient_cards[i].find_element_by_class_name('CCU-checkbox').click()
        for i in [2, 7, 11]:
            patient_cards[i].find_element_by_class_name('COVID-checkbox').click()
        for i in [10]:
            dropdown = Select(
                patient_cards[i].find_element_by_class_name('bounceback-dropdown').find_element_by_tag_name('select'))
            dropdown.select_by_visible_text('provC')
        for i in [4]:
            dropdown = Select(
                patient_cards[i].find_element_by_class_name('bounceback-dropdown').find_element_by_tag_name('select'))
            dropdown.select_by_visible_text('provA')

        submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
        submit_patient_forms_button.click()

        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # seens:  we expect that seen bouncebacks are assigned first, here i=4 to provA, and then that
        # pts are assigned to try to balance out total patients, and then COVID+CCU
        # unseens: we expect that unseen bouncebacks are assigned first, here 11th pt (i=10) to prov C.  we then expect
        # the dual-pos to be assigned in order:  2 to prov B, 11 to prov A; then CCU pos:  5 to provD; then COVID pos
        # 7 to prov B; then the dual negatives: 0 to prov C, and 14 to prov A
        rounder_cell_actual_text = []
        rounder_rows = self.browser.find_elements_by_id('id_assigned_patient_row')
        for rounder_row in rounder_rows:
            line_of_text = []
            rounder_cells = rounder_row.find_elements_by_tag_name('td')
            for cell in rounder_cells:
                line_of_text.append(cell.text)
            rounder_cell_actual_text.append(line_of_text)
        expected_text = [
            ['provB', '11 3 3', '', '', '', '', '4 10', '13 3 3', '3 8'],
            ['provC', '13 2 1', '', '', '', '', '', '13 2 1', '11 1'],
            ['provA', '10 2 0', '5', '', '2', '', '14 16', '14 3 0', '12 15'],
            ['provD', '11 1 2', '', '', '7 9 13', '', '', '14 4 2', '6']
        ]

    def test_patients_are_distributed_as_expected_CASE_many_max_limits(self):
        # not_seens, which are distributed
        # in order of dual-pos, CCU-pos, COVID-pos, and dual-neg
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('20')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for i in [0, 2, 5, 7, 10, 11, 14]:
            patient_cards[i].find_element_by_class_name('not-seen-checkbox').click()
        for i in [1, 2, 5, 6, 8, 11, 12]:
            patient_cards[i].find_element_by_class_name('CCU-checkbox').click()
        for i in [2, 7, 11]:
            patient_cards[i].find_element_by_class_name('COVID-checkbox').click()
        for i in [10]:
            dropdown = Select(
                patient_cards[i].find_element_by_class_name('bounceback-dropdown').find_element_by_tag_name('select'))
            dropdown.select_by_visible_text('provC')
        for i in [4]:
            dropdown = Select(
                patient_cards[i].find_element_by_class_name('bounceback-dropdown').find_element_by_tag_name('select'))
            dropdown.select_by_visible_text('provA')

        provA = Provider.objects.get(qgenda_name='provA')
        provA.max_COVID_census, provA.max_CCU_census, provA.max_total_census = 2, 4, 20
        provA.save()
        provB = Provider.objects.get(qgenda_name='provB')
        provB.max_COVID_census, provB.max_CCU_census, provB.max_total_census = 4, 5, 14
        provB.save()
        provC = Provider.objects.get(qgenda_name='provC')
        provC.max_COVID_census, provC.max_CCU_census, provC.max_total_census = 12, 12, 12
        provC.save()
        provD = Provider.objects.get(qgenda_name='provD')
        provD.max_COVID_census, provD.max_CCU_census, provD.max_total_census = 0, 0, 12
        provD.save()
        submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
        submit_patient_forms_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title,
                         f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
        # in this case, we have many limits on censuses, which are adhered to, except for provC getting its bounceback
        # w number 11
        table_actual_text = []
        table_rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for table_row in table_rows:
            line_of_text = []
            table_cells = table_row.find_elements_by_tag_name('td')
            for cell in table_cells:
                line_of_text.append(cell.text)
            table_actual_text.append(line_of_text)
        expected_text = [
            ['Unassigned', '', '', '', '', '', '', '0 0 0', '3 12 6 1 5'],
            ['provB', '11 3 3', '', '', '2, 7', '', '4', '14 5 3', ''],
            ['provC', '13 2 1', '', '', '', '', '', '13 2 1', '11 1'],
            ['provA', '10 2 0', '5', '', '2', '', '14 16', '14 3 0', '12 15'],
            ['provD', '11 1 2', '', '', '7 9 13', '', '', '14 4 2', '6']
        ]

    def test_multiple_random_iterations_do_not_leave_any_patients_off_list_or_list_any_twice(self):

        for i in range(10):
            helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
            self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
            self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
            patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
            patient_count = random.randint(1, 50)
            patient_count_box.send_keys(f'{patient_count}')
            submit_button = self.browser.find_element_by_id('id_submit_count_button')
            submit_button.click()
            self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))

            self.assertEqual(self.browser.title,
                             f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
            self.browser.maximize_window()
            for patient_card in self.browser.find_elements_by_class_name('patient-card'):
                if random.random() < 0.2:
                    patient_card.find_element_by_class_name('not-seen-checkbox').click()
                if random.random() < 0.3:
                    patient_card.find_element_by_class_name('CCU-checkbox').click()
                if random.random() < 0.15:
                    patient_card.find_element_by_class_name('COVID-checkbox').click()
                if random.random() < 0.15:
                    bounceback_dropdown = Select(
                        patient_card.find_element_by_class_name('bounceback-dropdown').find_element_by_tag_name(
                            'select'))
                    random_provider = random.choice(['provA', 'provB', 'provC', 'provD'])
                    bounceback_dropdown.select_by_visible_text(random_provider)
            submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
            submit_patient_forms_button.click()
            self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
            self.assertEqual(self.browser.title,
                             f'Compose Assignment Email - {timezone.localdate().strftime("%-m/%-d/%y")}')
            all_assigned_patient_numbers = []
            table_rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for table_row in table_rows:
                try:
                    seen_dual_neg_pts = [int(text_value) for text_value in
                                         table_row.find_element_by_id('id_dual_neg_patients').text.split(' ')]
                    for pt in seen_dual_neg_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
                try:
                    not_seen_pts = [int(text_value) for text_value in
                                    table_row.find_element_by_id('id_not_seen_patients').text.split(' ')]
                    for pt in not_seen_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
                try:
                    CCU_pts = [int(text_value) for text_value in
                               table_row.find_element_by_id('id_CCU_patients').text.split(' ')]
                    for pt in CCU_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
                try:
                    COVID_pts = [int(text_value) for text_value in
                                 table_row.find_element_by_id('id_COVID_patients').text.split(' ')]
                    for pt in COVID_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
                try:
                    dual_pos_pts = [int(text_value) for text_value in
                                    table_row.find_element_by_id('id_dual_pos_patients').text.split(' ')]
                    for pt in dual_pos_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
                try:
                    bounceback_pts = [int(text_value) for text_value in
                                      table_row.find_element_by_id('id_bounceback_patients').text.split(' ')]
                    for pt in bounceback_pts:
                        all_assigned_patient_numbers.append(pt)
                except ValueError:
                    pass
            sorted_assigned_patient_numbers = sorted(all_assigned_patient_numbers)
            self.assertEqual(sorted_assigned_patient_numbers, [number for number in range(1, patient_count + 1)])
        # self.assertContains()

    def test_email_can_be_sent(self):
        self.fail('finish')
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/patient_count/{timezone.localdate().strftime("%m-%d-%y")}')
        self.assertEqual(self.browser.title, f'Patient Count - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_count_box = self.browser.find_element_by_id('id_count_to_distribute')
        patient_count_box.send_keys('31')
        submit_button = self.browser.find_element_by_id('id_submit_count_button')
        submit_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Patient Characteristics - {timezone.localdate().strftime("%-m/%-d/%y")}')
        patient_cards = self.browser.find_elements_by_class_name('patient-card')
        for i in [0, 13, 14, 17]:
            patient_cards[i].find_element_by_class_name('CCU-checkbox').click()
            patient_cards[i + 3].find_element_by_class_name('COVID-checkbox').click()
        submit_patient_forms_button = self.browser.find_element_by_id('id_submit_patient_forms')
        submit_patient_forms_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.browser.get(f'{self.live_server_url}/send_distribution/{timezone.localdate().strftime("%m-%d-%y")}')
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        email_html = mail.outbox[0].alternatives[0][0]
        self.assertIn('CCU/COVID', email_html)
        self.assertIn(f'Pt assignment - {timezone.localtime().strftime("%m/%d/%y   %a")}', mail.outbox[0].subject)


class ProviderUpdateTests(FunctionalTest):
    def test_displays_qgenda_name_and_initial_values(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/update_provider/provC')
        self.assertEqual(self.browser.find_element_by_id('id_display_name').get_attribute('value'), 'provC')
        self.assertEqual(self.browser.find_element_by_id('id_max_total_census').get_attribute('value'), '17')
        self.assertEqual(self.browser.find_element_by_id('id_max_CCU_census').get_attribute('value'), '17')
        self.assertEqual(self.browser.find_element_by_id('id_max_COVID_census').get_attribute('value'), '17')

    def test_selecting_presets_and_submitting_changes_max_values_and_navigates_to_current_rounders(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/update_provider/provC')
        teaching_button = self.browser.find_element_by_id('id_set_max_censuses_to_teaching')
        teaching_button.click()
        provider = Provider.objects.get(qgenda_name='provC')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 12)
        default_button = self.browser.find_element_by_id('id_reset_max_censuses_to_default')
        default_button.click()
        provider = Provider.objects.get(qgenda_name='provC')
        self.assertEqual(provider.max_total_census, 17)
        self.assertEqual(provider.max_CCU_census, 17)
        self.assertEqual(provider.max_COVID_census, 17)
        orienting_button = self.browser.find_element_by_id('id_set_max_censuses_to_orienting')
        orienting_button.click()
        provider = Provider.objects.get(qgenda_name='provC')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 12)
        covid_free_button = self.browser.find_element_by_id('id_set_max_censuses_to_COVID_free')
        covid_free_button.click()
        provider = Provider.objects.get(qgenda_name='provC')
        self.assertEqual(provider.max_total_census, 12)
        self.assertEqual(provider.max_CCU_census, 12)
        self.assertEqual(provider.max_COVID_census, 0)

    def test_manually_inputting_valid_values_and_submitting_changes_max_values_and_navigates_to_current_rounders(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/update_provider/provC')
        self.browser.find_element_by_id('id_display_name').click()
        self.browser.find_element_by_id('id_display_name').send_keys('NewProv')
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('13')
        self.browser.find_element_by_id('id_max_CCU_census').click()
        self.browser.find_element_by_id('id_max_CCU_census').send_keys('6')
        self.browser.find_element_by_id('id_max_COVID_census').click()
        self.browser.find_element_by_id('id_max_COVID_census').send_keys('4')
        submit_provider_updates_button = self.browser.find_element_by_id('id_submit_provider_updates')
        submit_provider_updates_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Current Rounders - {timezone.localdate().strftime("%-m/%-d/%y")}')
        provider = Provider.objects.get(qgenda_name='provC')
        self.assertEqual(provider.display_name, 'NewProv')
        self.assertEqual(provider.max_total_census, 13)
        self.assertEqual(provider.max_CCU_census, 6)
        self.assertEqual(provider.max_COVID_census, 4)
        census_rows = self.browser.find_elements_by_id('id_starting_census_row')
        rounder_cell = census_rows[1].find_element_by_id('id_rounder_cell')
        self.assertEqual(rounder_cell.find_element_by_id('id_rounder_name').text, 'NewProv')
        self.assertEqual(rounder_cell.find_element_by_class_name('custom-max-total-census').text, '13')
        self.assertEqual(rounder_cell.find_element_by_class_name('custom-max-CCU-census').text, '6')
        self.assertEqual(rounder_cell.find_element_by_class_name('custom-max-COVID-census').text, '4')

    def test_inputting_invalid_values_and_submitting_stays_on_page_and_shows_error(self):
        helper_fxns.helper_fxn_create_distribution_with_4_rounder_line_items_and_2_non_rounder_line_items()
        self.browser.get(f'{self.live_server_url}/update_provider/provC')
        self.browser.find_element_by_id('id_display_name').click()
        self.browser.find_element_by_id('id_display_name').send_keys('provB')
        submit_provider_updates_button = self.browser.find_element_by_id('id_submit_provider_updates')
        submit_provider_updates_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update provC')
        error_message = self.browser.find_element_by_class_name('invalid-feedback')
        self.assertEqual(error_message.text, 'Provider with this Display name already exists.')
        self.browser.find_element_by_id('id_display_name').click()
        self.browser.find_element_by_id('id_display_name').send_keys('provC')
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('130')
        submit_provider_updates_button = self.browser.find_element_by_id('id_submit_provider_updates')
        submit_provider_updates_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update provC')
        error_message = self.browser.find_element_by_class_name('invalid-feedback')
        self.assertEqual(error_message.text, 'Ensure this value is less than or equal to 30.')
        self.browser.find_element_by_id('id_max_total_census').click()
        self.browser.find_element_by_id('id_max_total_census').send_keys('10')
        self.browser.find_element_by_id('id_max_CCU_census').click()
        self.browser.find_element_by_id('id_max_CCU_census').send_keys('-1')
        submit_provider_updates_button = self.browser.find_element_by_id('id_submit_provider_updates')
        submit_provider_updates_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update provC')
        error_message = self.browser.find_element_by_class_name('invalid-feedback')
        self.assertEqual(error_message.text, 'Ensure this value is greater than or equal to 0.')
        self.browser.find_element_by_id('id_max_CCU_census').click()
        self.browser.find_element_by_id('id_max_CCU_census').send_keys('4')
        self.browser.find_element_by_id('id_max_COVID_census').click()
        self.browser.find_element_by_id('id_max_COVID_census').send_keys('gh')
        submit_provider_updates_button = self.browser.find_element_by_id('id_submit_provider_updates')
        submit_provider_updates_button.click()
        self.wait_for(lambda: self.browser.find_elements_by_tag_name('body'))
        self.assertEqual(self.browser.title, f'Update provC')
