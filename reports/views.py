from django.shortcuts import render, redirect
from django.views import View
from datetime import datetime
from task_manager.models import Project
from .models import ProjectInfo, UserInfo, UserInProject
from django.db.models import Q

class Report(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        projects = Project.objects.filter(Q(owner=request.user) | Q(members=request.user)).all()
        p_info_list = []
        u_info = UserInfo(user)
        user_in_projects = []

        for p in projects:
            p_info = ProjectInfo(p)
            u_info.analyze_project(p)
            p_info_list.append(p_info)
            user_in_projects.append(UserInProject(user, p))

        data = {"user": user,
                "first": user.username[0],
                "p_info": p_info_list,
                "u_info": u_info,
                "u_in_p": user_in_projects,
                'time': datetime.today()
                }
        return render(request, 'report.html', data)
