from django import forms
from django.core.mail import send_mail
from django.shortcuts import render, redirect, reverse
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from .forms import RounderStartingCensusForm, BaseStartingCensusFormset, PatientCountForm, \
    BasePatientCharacteristicsFormset, ProviderUpdateForm, AddRounderFromExistingProvidersForm, AddNewRounderForm, \
    EmailDistributionForm
from .models import Distribution, StartingCensus, Patient, Provider, QGendaDataSet


def current_rounders_view(request, date_str=None):
    if not date_str:
        date = timezone.localdate()
        date_str = timezone.datetime.strftime(date, '%m-%d-%y')
    else:
        date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.get_last_for_date_or_create_new(date=date)
    StartingCensusFormset = forms.modelformset_factory(form=RounderStartingCensusForm,
                                                       formset=BaseStartingCensusFormset,
                                                       model=StartingCensus)
    if request.method != 'POST':
        starting_census_formset = StartingCensusFormset(
            queryset=StartingCensus.objects.filter(distribution_line_item__distribution=distribution).order_by(
                'distribution_line_item__position_in_batting_order'))
    else:
        starting_census_formset = StartingCensusFormset(data=request.POST,
                                                        queryset=StartingCensus.objects.filter(
                                                            distribution_line_item__distribution=distribution).order_by(
                                                            'distribution_line_item__position_in_batting_order'))
        if starting_census_formset.is_valid():
            starting_census_formset.save()
            return redirect(reverse('distribution:patient_count',
                                    kwargs={'date_str': date_str}))
    context = {'date': date, 'starting_census_formset': starting_census_formset}
    return render(request, 'distribution/current_rounders.html', context)


def modify_rounders_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    if request.method != 'POST':
        add_rounder_from_existing_form = AddRounderFromExistingProvidersForm(distribution=distribution)
    else:
        add_rounder_from_existing_form = AddRounderFromExistingProvidersForm(distribution=distribution,
                                                                             data=request.POST)
        if add_rounder_from_existing_form.is_valid():
            add_rounder_from_existing_form.save()
            return redirect(reverse('distribution:modify_rounders', kwargs={'date_str': date_str}))
    context = {'date': date, 'distribution': distribution,
               'add_rounder_from_existing_form': add_rounder_from_existing_form}
    return render(request, 'distribution/modify_rounders.html', context=context)


def add_rounder_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    if request.method != 'POST':
        add_new_rounder_form = AddNewRounderForm(distribution=distribution)
    else:
        add_new_rounder_form = AddNewRounderForm(distribution=distribution, data=request.POST)
        if add_new_rounder_form.is_valid():
            add_new_rounder_form.save()
            return redirect(reverse('distribution:modify_rounders', kwargs={'date_str': date_str}))
    context = {'date': date, 'distribution': distribution,
               'add_new_rounder_form': add_new_rounder_form}
    return render(request, 'distribution/add_rounder.html', context=context)


# not a visible view
def make_next_up_view(request, line_item_id, date_str=timezone.localdate().strftime("%m-%d-%y")):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    distribution.move_line_item_to_next_up(
        next_up_line_item=distribution.return_ordered_rounder_line_items().get(id=line_item_id))
    referer_url = request.META.get('HTTP_REFERER')
    if referer_url:
        return redirect(referer_url)
    else:
        return redirect(reverse('distribution:current_rounders',
                                kwargs={'date_str': date_str}))


# not a visible view
def shift_up_in_batting_order_view(request, line_item_id, date_str=timezone.localdate().strftime("%m-%d-%y")):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    distribution.shift_up_in_batting_order(
        rising_line_item=distribution.return_ordered_rounder_line_items().get(id=line_item_id))
    referer_url = request.META.get('HTTP_REFERER')
    if referer_url:
        return redirect(referer_url)
    else:
        return redirect(reverse('distribution:modify_rounders',
                                kwargs={'date_str': date_str}))


# not a visible view
def delete_rounder_view(request, line_item_id, date_str=timezone.localdate().strftime("%m-%d-%y")):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    distribution.delete_rounder(line_item=distribution.return_ordered_rounder_line_items().get(id=line_item_id))
    referer_url = request.META.get('HTTP_REFERER')
    if referer_url:
        return redirect(referer_url)
    else:
        return redirect(reverse('distribution:modify_rounders',
                                kwargs={'date_str': date_str}))


# not a visible view
def reset_to_qgenda_view(request, date_str=timezone.localdate().strftime("%m-%d-%y")):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    QGendaDataSet.objects.filter(date=date).delete()
    Distribution.objects.create_new_distribution_from_qgenda_data(date=date)
    return redirect(reverse('distribution:current_rounders',
                            kwargs={'date_str': date_str}))


def patient_count_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    if request.method != 'POST':
        patient_count_form = PatientCountForm(instance=distribution)
    else:
        patient_count_form = PatientCountForm(instance=distribution, data=request.POST)
        if patient_count_form.is_valid():
            patient_count_form.save()
            return redirect(reverse('distribution:patient_characteristics', kwargs={'date_str': date_str}))
    context = {'date': date, 'ordered_line_items': distribution.return_ordered_rounder_line_items(),
               'patient_count_form': patient_count_form}
    return render(request, 'distribution/patient_count.html', context)


def patient_characteristics_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    distribution = Distribution.objects.filter(date=date).last()
    PatientCharacteristicsFormset = forms.modelformset_factory(model=Patient,
                                                               fields=['CCU', 'COVID', 'not_seen', 'bounce_to'],
                                                               formset=BasePatientCharacteristicsFormset)
    if request.method != 'POST':
        patient_characteristics_formset = PatientCharacteristicsFormset(distribution_id=distribution.id)
    else:
        patient_characteristics_formset = PatientCharacteristicsFormset(distribution_id=distribution.id,
                                                                        data=request.POST)
        if patient_characteristics_formset.is_valid():
            patient_characteristics_formset.save()
            distribution.assign_all_patients()
            return redirect(reverse('distribution:compose_patient_assignments_email', kwargs={'date_str': date_str}))
    context = {'date': date, 'ordered_line_items': distribution.return_ordered_rounder_line_items(),
               'patient_characteristics_formset': patient_characteristics_formset}
    return render(request, 'distribution/patient_characteristics.html', context)


def assemble_patient_assignment_context(date):
    distribution = Distribution.objects.filter(date=date).last()
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
                                                          distribution_line_item__isnull=True, not_seen=False).count()
    unassigned_seen_CCU_census = Patient.objects.filter(distribution=distribution,
                                                        distribution_line_item__isnull=True, not_seen=False).filter(
        CCU=True).count()
    unassigned_seen_COVID_census = Patient.objects.filter(distribution=distribution,
                                                          distribution_line_item__isnull=True, not_seen=False).filter(
        COVID=True).count()
    unassigned_patient_dict.update(
        {'seen_bounceback_pts': seen_bounceback_pts, 'seen_dual_pos_pts': seen_dual_pos_pts,
         'seen_ccu_pos_pts': seen_ccu_pos_pts,
         'seen_covid_pos_pts': seen_covid_pos_pts, 'seen_dual_neg_pts': seen_dual_neg_pts, 'not_seen_pts': not_seen_pts,
         'unassigned_seen_total_census': unassigned_seen_total_census,
         'unassigned_seen_CCU_census': unassigned_seen_CCU_census,
         'unassigned_seen_COVID_census': unassigned_seen_COVID_census})
    return {'date': date, 'ordered_line_items': line_items,
            'patient_assignment_dict': patient_assignment_dict, 'unassigned_patient_dict': unassigned_patient_dict}


def compose_patient_assignments_email_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    context = assemble_patient_assignment_context(date=date)
    if request.method != 'POST':
        email_distribution_form = EmailDistributionForm(distribution=Distribution.objects.filter(date=date).last())
    else:
        email_distribution_form = EmailDistributionForm(distribution=Distribution.objects.filter(date=date).last(),
                                                        data=request.POST)
        if email_distribution_form.is_valid():
            distribution_email = email_distribution_form.save()
            distribution_email.send_distribution_email()
            return redirect(reverse('distribution:view_patient_assignments', kwargs={'date_str':date_str}))
    context.update({'email_distribution_form': email_distribution_form})
    return render(request, 'distribution/compose_patient_assignments_email.html', context)

def view_patient_assignments_view(request, date_str):
    date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
    context = assemble_patient_assignment_context(date=date)
    return render(request, "distribution/view_patient_assignments.html", context)

# def send_distribution(request, date_str):
#     date = timezone.datetime.strptime(date_str, '%m-%d-%y').date()
#     patient_assignment_context = assemble_patient_assignment_context(date=date)
#     subject = f'Pt assignment - {timezone.localtime().strftime("%m/%d/%y   %a   %X %p")}'
#     from_email = 'noreply@kalusinator.com'
#     recipient_list = ['bobearl@mac.com', 'rmkalus@evergreenhealthcare.org', 'rkalus@gmail.com']
#     # html_message = format_html(get_template(template_name='distribution/patient_assignment_table.html').render(
#     #     context=patient_assignment_context))
#     html_message = render_to_string('distribution/simple_assignment_table.html', patient_assignment_context)
#     message = html_message
#     send_mail(subject=subject, from_email=from_email, recipient_list=recipient_list, message=message,
#               html_message=html_message)
#     return redirect(reverse('distribution:patient_assignments', kwargs={'date_str': date_str}))


def update_provider_view(request, provider_qgenda_name):
    provider = Provider.objects.get(qgenda_name=provider_qgenda_name)
    if request.method != 'POST':
        provider_update_form = ProviderUpdateForm(instance=provider)
    else:
        provider_update_form = ProviderUpdateForm(instance=provider, data=request.POST)
        if provider_update_form.is_valid():
            provider_update_form.save()
            return redirect(reverse('distribution:current_rounders',
                                    kwargs={'date_str': timezone.localdate().strftime('%m-%d-%y')}))
    context = {'provider_update_form': provider_update_form}
    return render(request, 'distribution/update_provider.html', context=context)


def set_max_censuses(request, census_track, provider_qgenda_name):
    # no associated view, but resets given provider censuses to the ones for a given track
    provider = Provider.objects.get(qgenda_name=provider_qgenda_name)
    provider.set_max_censuses_to_census_track(census_track=census_track)
    return redirect(reverse('distribution:update_provider', kwargs={'provider_qgenda_name': provider_qgenda_name}))
