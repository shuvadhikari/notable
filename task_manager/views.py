import datetime
import json
import random

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from reports.models import ProjectInfo
from .models import Task, Project, Team

from bardapi import Bard
import os


class Projects(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        projects = Project.objects.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
        teams = Team.objects.all()
        list = []

        for p in projects:
            # if p.owner == user or p.members.filter(user).exists():
            list.append(ProjectInfo(p))

        data = {
            "user": user,
            "first": user.username[0],
            "other_users": User.objects.filter(~Q(id=user.id)).all(),
            "teams": teams,
            "projects": list,
        }
        return render(request, 'projects.html', data)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        if request.POST.get('type') == "project":
            name = request.POST['name']
            description = request.POST['desc']
            details = request.POST['details']
            owner = request.user

            n = random.randint(1, 7)
            pf_url = f'/media/project-logos/{n}.png'

            proj = Project.objects.create(
                name=name,
                description=description,
                details=details,
                owner=owner,
                profile_photo=pf_url
            )
            proj.save()

            for user in request.POST.getlist('users', []):
                if user.split('-')[1] == 'user':
                    proj.members.add(User.objects.get(id=int(user.split('-')[0])))
                elif user.split('-')[1] == 'team':
                    for userObj in Team.objects.get(id=int(user.split('-')[0])).members.all():
                        proj.members.add(userObj)
        else:
            name = request.POST['name']
            description = request.POST['desc']
            owner = request.user
            user_ids = request.POST.getlist('members', [])

            team = Team.objects.create(
                name=name,
                description=description,
                owner=owner
            )
            team.save()
            for user in user_ids:
                team.members.add(User.objects.get(id=user))

        return redirect('boards')


class MangeProject(View):
    def post(self, request, id):
        Project.objects.filter(id=id).delete()

        response = JsonResponse({"message": "OK"})
        response.status_code = 200
        return response


class Tasks(View):
    def get(self, request, id):
        if not request.user.is_authenticated:
            return redirect("signIn")

        proj = Project.objects.filter(id=id).first()
        user = request.user
        users = User.objects.filter(Q(id__in=list(proj.members.all().values_list('id', flat=True))) | Q(id=proj.owner.id))
        data = {
            "user": user,
            "first": user.username[0],
            "other_users": users,
            "tasks": proj.task_set.all(),
            'proj': proj,
            "can_add": user == proj.owner
        }
        return render(request, 'tasks.html', data)

    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        name = request.POST['name']
        description = request.POST['desc']
        status = 'T'
        end_time = request.POST['date']

        task = Task(
            name=name,
            description=description,
            status=status,
            end_time=end_time,
            project_id=id
        )
        task.save()

        for user in request.POST.getlist('users', []):
            task.assigned_to.add(User.objects.get(id=user))

        return redirect('tasks', id=id)


class ManegeTasks(View):
    def post(self, request, id):
        if not request.user.is_authenticated:
            response = JsonResponse({"error": "Invalid User"})
            response.status_code = 403
            return response

        user = request.user

        type = request.POST['type']
        if type == 'edit_status':
            task_id = request.POST['task_id']
            status = request.POST['board_id']

            task = Task.objects.filter(id=task_id).first()

            if status in ['O', 'B', 'L'] or task.status in ['O', 'B', 'L']:
                if user == task.project.owner:
                    task.status = status
                    task.save()

                else:
                    response = JsonResponse({"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response
            else:
                if user == task.assigned_to or user == task.project.owner:
                    task.status = status
                    if status == 'D':
                        task.start_time = datetime.datetime.today().date()
                    task.save()
                else:
                    response = JsonResponse({"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response

            response = JsonResponse({"message": "OK"})
            response.status_code = 200
            return response

        if type == 'edit_end_time':

            task_id = request.POST['task_id']
            end_time = request.POST['new_end_time']

            task = Task.objects.filter(id=task_id).first()

            if user == task.project.owner:
                task.end_time = end_time
                task.save()

                response = JsonResponse({"message": "OK"})
                response.status_code = 200
                return response

            else:
                response = JsonResponse({"error": "You Do Not Have Permission"})
                response.status_code = 403
                return response


def chat_gpt(request):
    if request.GET.get('q'):
        os.environ['_BARD_API_KEY'] = "XAjsS_NzgSqMNgYKYSniT1_gle-QuAGXPnnrZhpHZ9idu90gekA8537HHfHHYrl6wEnHwQ."
        return JsonResponse({
            "role": "assistant",
            "content": Bard().get_answer(
                request.GET.get('q')
            )['content']
        })
    else:
        return JsonResponse({
            "role": "assistant",
            "content": "invalid data"
        })