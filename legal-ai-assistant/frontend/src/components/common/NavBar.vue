<!-- src/components/common/NavBar.vue -->
<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <router-link to="/chat" class="navbar-brand">
        <i class="bi bi-scales me-2"></i>
        Legal AI Assistant
      </router-link>
      
      <button 
        class="navbar-toggler" 
        type="button" 
        data-bs-toggle="collapse" 
        data-bs-target="#navbarNav"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <router-link to="/chat" class="nav-link" active-class="active">
              <i class="bi bi-chat-dots me-1"></i>
              Chat
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/documents" class="nav-link" active-class="active">
              <i class="bi bi-file-earmark-text me-1"></i>
              Documents
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/history" class="nav-link" active-class="active">
              <i class="bi bi-clock-history me-1"></i>
              History
            </router-link>
          </li>
        </ul>
        
        <ul class="navbar-nav">
          <li class="nav-item dropdown">
            <a 
              class="nav-link dropdown-toggle" 
              href="#" 
              id="userDropdown" 
              role="button" 
              data-bs-toggle="dropdown"
            >
              <i class="bi bi-person-circle me-1"></i>
              {{ authStore.username }}
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
              <li>
                <router-link to="/settings" class="dropdown-item">
                  <i class="bi bi-gear me-2"></i>
                  Settings
                </router-link>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <a class="dropdown-item" href="#" @click.prevent="handleLogout">
                  <i class="bi bi-box-arrow-right me-2"></i>
                  Logout
                </a>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
  font-weight: 600;
  font-size: 1.3rem;
}

.nav-link {
  transition: color 0.3s;
}

.nav-link:hover {
  color: #fff !important;
}

.nav-link.active {
  font-weight: 500;
}
</style>