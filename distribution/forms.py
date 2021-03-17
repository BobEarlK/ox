from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field, HTML
from crispy_forms.bootstrap import InlineCheckboxes
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from .models import StartingCensus, SecondaryRoleForLineItem, DistributionLineItem, Distribution, Patient, Provider, \
    RounderRole, DistributionEmail, EmailAddressee


class RounderStartingCensusForm(forms.ModelForm):
    class Meta:
        model = StartingCensus
        fields = ['distribution_line_item', 'total_census', 'CCU_census', 'COVID_census']
        required = ['distribution_line_item', 'total_census']

    def clean_distribution_line_item(self):
        cleaned_data = super().clean()
        line_item = cleaned_data['distribution_line_item']
        try:
            self.instance = line_item.startingcensus
        except ObjectDoesNotExist:
            pass
        return line_item

    def clean_CCU_census(self):
        cleaned_data = super().clean()
        if not type(cleaned_data['CCU_census']) == int:
            cleaned_data['CCU_census'] = 0
        return cleaned_data['CCU_census']

    def clean_COVID_census(self):
        cleaned_data = super().clean()
        if not type(cleaned_data['COVID_census']) == int:
            cleaned_data['COVID_census'] = 0
        return cleaned_data['COVID_census']


class BaseStartingCensusFormset(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.extra = 0
        super().__init__(*args, **kwargs)
        for index, form in enumerate(self.forms):
            form.id = index + 1
            form.helper = FormHelper()
            form.helper.form_id = 'id_starting_census_form'
            form.helper.form_class = 'starting-census'
            form.helper.form_tag = False
            form.helper.disable_csrf = True
            form.helper.form_show_labels = False
            next_up_link_html = """<a id="id_next_up_link" href="{% url 'distribution:make_next_up' line_item_id=""" + \
                                str(form.instance.distribution_line_item.id) + \
                                """ date_str=date|date:'m-d-y' %}" class="next-up-link table-cell-button col-1">""" + \
                                """&#8593;</a>"""
            form.helper.layout = Layout(
                Div(
                    Div(
                        HTML(next_up_link_html),
                        Field('id', type='hidden', value=form.id),
                        Field('distribution_line_item', type='hidden', value=form.instance.distribution_line_item.id),
                        # rounder-html inserted here, after layout[0][0][2] (hidden line_item field) in position [0][0][3]
                        # rounder-supplemental html inserted here (e.g. secondary roles, max censuses) in position [0][0][4]
                        css_class='col-5 row ml-2', id='id_rounder_column'),
                    Div(
                        Field('total_census', id='id_total_census_field', placeholder='Total',
                              css_class='census-input', wrapper_class='col-4'),
                        Field('CCU_census', id='id_CCU_census_field', placeholder='CCU', css_class='census-input',
                              wrapper_class='col-4'),
                        Field('COVID_census', id='id_COVID_census_field', placeholder='COVID',
                              css_class='census-input', wrapper_class='col-4'),
                        css_class='col-7 row mx-auto', id='id_censuses_column'),
                    id='id_starting_census_row', css_class='row'
                )
            )
            # insert the rounder_html after the hidden fields, i.e. it will then be in layout position [0][3]
            this_rounder = form.instance.distribution_line_item.provider
            rounder_html = f'''<div id="id_rounder_cell" class="col-8">''' + \
                           f'''<p id="id_rounder_text" class="rounder-text">''' + \
                           f'''<a href="{{% url 'distribution:update_provider' provider_qgenda_name=''' + \
                           f"'{this_rounder.qgenda_name}'" + \
                           '''%}" id="id_rounder_name" class="rounder-name-class">''' + \
                           f'''{this_rounder.display_name}</a></p>'''
            # construct the supplemental_html_after_the_rounder_html, i.e. will then be in layout position [0][4]
            salient_supplemental_html = ""  # will be blank unless meets certain criteria
            if this_rounder.max_total_census != 17:
                salient_supplemental_html += \
                    f'''<span class="custom-max-total-census">{this_rounder.max_total_census}</span>'''
            if this_rounder.max_CCU_census != 17:
                salient_supplemental_html += \
                    f'''<span class="custom-max-CCU-census">{this_rounder.max_CCU_census}</span>'''
            if this_rounder.max_COVID_census != 17:
                salient_supplemental_html += \
                    f'''<span class="custom-max-COVID-census">{this_rounder.max_COVID_census}</span>'''
            if form.instance.distribution_line_item.secondary_roles_for_line_items.count():
                try:
                    form.instance.distribution_line_item.secondary_roles_for_line_items.get(
                        secondary_role__qgenda_name__endswith='AM TRIAGE')
                    salient_supplemental_html += f"""<span class="am-triage">a.m. triage</span>"""
                except SecondaryRoleForLineItem.DoesNotExist:
                    pass
                try:
                    form.instance.distribution_line_item.secondary_roles_for_line_items.get(
                        secondary_role__qgenda_name__endswith='PM TRIAGE')
                    salient_supplemental_html += f"""<span class="pm-triage">p.m. triage</span>"""
                except SecondaryRoleForLineItem.DoesNotExist:
                    pass
            supplemental_html = f'''<p id="id_rounder_supplemental_text" class="rounder-supplemental-text">''' + \
                                f'''{salient_supplemental_html}</p></div>'''
            form.helper.layout[0][0].insert(3, HTML(rounder_html))
            form.helper.layout[0][0].insert(4, HTML(supplemental_html))


class AddRounderFromExistingProvidersForm(forms.ModelForm):
    class Meta:
        model = DistributionLineItem
        fields = ['provider']

    def __init__(self, *args, **kwargs):
        self.distribution = kwargs.pop('distribution')
        super().__init__(*args, **kwargs)
        unused_providers = Provider.objects.exclude(
            line_items__in=self.distribution.return_ordered_rounder_line_items()).order_by('qgenda_name')
        self.fields['provider'].queryset = unused_providers
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = 'id_add_rounder_from_existing_form'
        self.helper.form_method = 'post'
        self.helper.field_class = 'text-center'
        self.helper.add_input(Submit('submit', 'Add', css_id='id_add_rounder_from_existing_button'))

    def save(self, *args, **kwargs):
        rounder_line_item = super().save(*args, **kwargs, commit=False)
        rounder_role = RounderRole.objects.get_or_create(qgenda_name='Added from existing', initial_sort_key=20)[0]
        rounder_line_item.distribution = self.distribution
        rounder_line_item.rounder_role = rounder_role
        rounder_line_item.position_in_batting_order = rounder_line_item.distribution.return_ordered_rounder_line_items().count() + 1
        rounder_line_item.save()
        StartingCensus.objects.create(distribution_line_item=rounder_line_item)
        return rounder_line_item


class AddNewRounderForm(forms.ModelForm):
    input_name = forms.CharField(max_length=11)

    class Meta:
        model = DistributionLineItem
        fields = []

    def __init__(self, *args, **kwargs):
        self.distribution = kwargs.pop('distribution')
        self.provider = None
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = 'id_add_new_rounder_form'
        self.helper.form_method = 'post'
        self.helper.field_class = 'text-center'
        self.helper.add_input(Submit('submit', 'Add', css_id='id_add_new_rounder_button'))

    def clean(self):
        input_name = self.cleaned_data['input_name']
        try:
            provider = Provider.objects.get(qgenda_name=input_name)
        except ObjectDoesNotExist:
            try:
                provider = Provider.objects.get(display_name=input_name)
            except ObjectDoesNotExist:
                provider = Provider.objects.get_or_create(display_name=f'_{input_name}',
                                                          qgenda_name=f'_{input_name}')[0]
        self.provider = provider

    def save(self, *args, **kwargs):
        rounder_line_item = super().save(*args, **kwargs, commit=False)
        rounder_role = RounderRole.objects.get_or_create(qgenda_name='Added Manually', initial_sort_key=20)[0]
        rounder_line_item.distribution = self.distribution
        rounder_line_item.provider = self.provider
        if self.provider in Provider.objects.filter(line_items__in=self.distribution.line_items.all()):
            return None
        rounder_line_item.rounder_role = rounder_role
        rounder_line_item.position_in_batting_order = rounder_line_item.distribution.return_ordered_rounder_line_items().count() + 1
        rounder_line_item.save()
        StartingCensus.objects.create(distribution_line_item=rounder_line_item)
        return rounder_line_item


class PatientCountForm(forms.ModelForm):
    class Meta:
        model = Distribution
        fields = ['count_to_distribute']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id_patient_count_to_distribute_form'
        self.helper.field_class = 'col-3 my-5 mx-auto'
        self.helper.form_show_labels = False
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit', css_id='id_submit_count_button', css_class='btn-lg'))

    def save(self, *args, **kwargs):
        distribution = super().save(*args, **kwargs)
        distribution.patients.all().delete()
        for i in range(distribution.count_to_distribute):
            Patient.objects.create(distribution=distribution, number_designation=i + 1)
        return distribution


class PatientCharacteristicsForm(forms.ModelForm):
    bounce_to = forms.ModelChoiceField(empty_label='', to_field_name='display_name', queryset=None)

    class Meta:
        model = Patient
        fields = ['number_designation', 'CCU', 'COVID', 'not_seen', 'bounce_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bounce_to'].queryset = self.instance.distribution.return_alphabetical_rounders()


class BasePatientCharacteristicsFormset(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        distribution = Distribution.objects.get(id=kwargs.pop('distribution_id'))
        self.extra = 0
        super().__init__(*args, **kwargs)
        self.queryset = distribution.patients.all()
        for index, form in enumerate(self.forms):
            form.fields['bounce_to'].queryset = distribution.return_alphabetical_rounders()
            form.helper = FormHelper()
            form.helper.form_id = 'id_patient_characteristics_form'
            form.helper.form_class = 'dummy-form-class'
            form.helper.form_tag = False
            form.helper.disable_csrf = True
            form.helper.layout = Layout(
                Div(
                    Field('id', type='hidden', value=form.instance.id),  # hidden id field to add id to POST data
                    Field('CCU', wrapper_class='CCU-checkbox'),
                    css_class='form-row CCU-row'),
                Div(
                    Field('COVID', wrapper_class='COVID-checkbox'),
                    css_class='form-row COVID-row'),
                Div(
                    Field('not_seen', wrapper_class='not-seen-checkbox'),
                    css_class='form-row not-seen-row'),
                Div(
                    Field('bounce_to', wrapper_class='bounceback-dropdown'),
                    css_class='form-row bounce-row'),

            )


class ProviderUpdateForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['display_name', 'max_total_census', 'max_CCU_census', 'max_COVID_census']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id_provider_update_form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit', css_id='id_submit_provider_updates', css_class='btn-lg',
                                     wrapper_class='text-center'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class EmailDistributionForm(forms.ModelForm):
    recipient_choices = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = DistributionEmail
        fields = ['subject']

    def __init__(self, *args, **kwargs):
        self.distribution = kwargs.pop('distribution')
        super().__init__(*args, **kwargs)
        if not EmailAddressee.objects.count():
            email_addressee_start_values = [('Hospitalists', 'DG-DptHospitalist-Physicians@evergreenhealthcare.org', True, True),
                                            ('Cheryl', 'CEHilbert@evergreenhealthcare.org', True, True),
                                            ('Susan', 'SMWarren@evergreenhealthcare.org', True, True),
                                            ('Intensivists', 'DptIntensivist-Physicians@evergreenhealthcare.org', True, False),
                                            ('ID docs', 'GrpInfectDisWoundCareMDs@evergreenhealthcare.org', True, False)]
            for (displayed_name, email_address, visible, pre_checked) in email_addressee_start_values:
                EmailAddressee.objects.get_or_create(displayed_name=displayed_name, email_address=email_address,
                                                     visible=visible, pre_checked=pre_checked)[0]
        self.fields['recipient_choices'].queryset = EmailAddressee.objects.filter(visible=True)
        self.initial['recipient_choices'] = EmailAddressee.objects.filter(pre_checked=True)
        instance = self.instance
        instance.distribution = self.distribution
        if self.distribution.date == timezone.localdate():
            self.initial['subject'] = f'Pt Assignment - {self.distribution.date.strftime("%a   %m/%d/%y")}'
        else:
            self.initial['subject'] = f'Pt Assignment for {self.distribution.date.strftime("%a %m/%d/%y")} ' + \
                                      f'sent on {timezone.localtime().strftime("%a %m/%d/%y")}'
        instance.html_message = render_to_string('distribution/simple_assignment_table.html',
                                                 instance.assemble_pt_assignment_context())
        # instance.save()
        self.helper = FormHelper()
        self.helper.form_id = 'id_email_distribution_form'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Div(
                HTML('<h5>Subject:</h5>'),
                Field('subject', wrapper_class='subject-field ml-5'),
                css_class='form-row subject-textbox', ),
            HTML('<h5>To:</h5>'),
            Div(
                Field('recipient_choices', wrapper_class='recipient_field ml-5', css_class='position-static'),
                css_class='form-row recipient-checkboxes'),
            Div(
                Submit('submit', 'Send Email', css_id='id_email_patient_distribution', css_class='btn-primary',
                       wrapper_class='text-center'), css_class='text-center')
        )
        self.helper.form_show_labels = False
        # self.helper.add_input(
        #     Submit('submit', 'Send Email', css_id='id_email_patient_distribution', css_class='btn-primary',
        #            wrapper_class='text-center'))

    def save(self, *args, **kwargs):
        instance = super().save()
        instance.recipient_text_field = []
        for recipient_choice in self.cleaned_data['recipient_choices']:
            instance.recipient_text_field.append(recipient_choice.email_address)
        instance.save()
        return instance
